from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.context_builder import ContextBuildError, MAX_CONTEXT_FILE_BYTES, build_context

REQUIRED = ("AGENTS.md", "docs/PROJECT_CONTEXT.md", "docs/CURRENT_STATUS.md",
            "docs/NEXT_STEPS.md", "docs/TASK_TEMPLATE.md", "docs/DEVELOPMENT_LOG.md")


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False, shell=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class ContextBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        git(self.root, "init", "-b", "feature/context-test")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Context Builder Test")
        for path in REQUIRED:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"# {path}\n", encoding="utf-8")
        source = self.root / "lib/main.dart"
        source.parent.mkdir(parents=True)
        source.write_text("void main() { print('pinned'); }\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "baseline")
        self.revision = git(self.root, "rev-parse", "HEAD")

    def tearDown(self):
        self.temp.cleanup()

    def build(self, paths=None):
        return build_context(root=self.root, task_id="context-test", source_revision=self.revision,
            required_paths=list(REQUIRED), source_paths=list(paths or ["lib/main.dart"]),
            allowed_patterns=["lib/**", "docs/**"], excluded_patterns=["lib/generated/**"])

    def test_full_text_hash_and_deterministic_package(self):
        first = self.build()
        self.assertEqual(first, self.build())
        doc = first["source_context"][0]
        self.assertEqual(doc["content"], "void main() { print('pinned'); }\n")
        self.assertEqual(doc["sha256"], hashlib.sha256(doc["content"].encode()).hexdigest())
        digest = first.pop("context_sha256")
        canonical = json.dumps(first, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(digest, hashlib.sha256(canonical).hexdigest())

    def test_reads_pinned_commit_not_mutable_worktree(self):
        (self.root / "lib/main.dart").write_text("uncommitted change", encoding="utf-8")
        self.assertIn("pinned", self.build()["source_context"][0]["content"])

    def test_rejects_traversal_and_protected_paths(self):
        for path in ("../outside", "secrets/token.txt", ".env"):
            with self.subTest(path=path), self.assertRaises(ContextBuildError):
                self.build([path])

    def test_rejects_out_of_scope_and_excluded_paths(self):
        with self.assertRaises(ContextBuildError):
            self.build(["AGENTS.md"])
        generated = self.root / "lib/generated/auto.dart"
        generated.parent.mkdir(parents=True)
        generated.write_text("generated", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "generated")
        self.revision = git(self.root, "rev-parse", "HEAD")
        with self.assertRaises(ContextBuildError):
            self.build(["lib/generated/auto.dart"])

    def test_rejects_symlink(self):
        outside = self.root.parent / (self.root.name + "-outside")
        outside.write_text("not to read", encoding="utf-8")
        try:
            (self.root / "lib/link.dart").symlink_to(outside)
            git(self.root, "add", "lib/link.dart")
            git(self.root, "commit", "-m", "symlink")
            self.revision = git(self.root, "rev-parse", "HEAD")
            with self.assertRaises(ContextBuildError):
                self.build(["lib/link.dart"])
        finally:
            outside.unlink(missing_ok=True)

    def test_rejects_binary_invalid_utf8_and_nul(self):
        for filename, raw in (("bad.bin", b"\xff\x80"), ("nul.txt", b"hello\x00world")):
            target = self.root / "lib" / filename
            target.write_bytes(raw)
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "binary")
        self.revision = git(self.root, "rev-parse", "HEAD")
        for filename in ("bad.bin", "nul.txt"):
            with self.subTest(filename=filename), self.assertRaises(ContextBuildError):
                self.build(["lib/" + filename])

    def test_rejects_per_file_and_combined_size_limits(self):
        large = self.root / "lib/too-large.dart"
        large.write_bytes(b"x" * (MAX_CONTEXT_FILE_BYTES + 1))
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "large file")
        self.revision = git(self.root, "rev-parse", "HEAD")
        with self.assertRaises(ContextBuildError):
            self.build(["lib/too-large.dart"])
        paths = []
        for index in range(3):
            relative = f"lib/large{index}.dart"
            (self.root / relative).write_bytes(b"x" * 200_000)
            paths.append(relative)
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "combined size")
        self.revision = git(self.root, "rev-parse", "HEAD")
        with self.assertRaises(ContextBuildError):
            self.build(paths)

    def test_rejects_unknown_revision(self):
        with self.assertRaises(ContextBuildError):
            build_context(root=self.root, task_id="context-test", source_revision="0" * 40,
                required_paths=list(REQUIRED), source_paths=["lib/main.dart"],
                allowed_patterns=["lib/**"], excluded_patterns=[])

    def test_prepare_persists_context_package(self):
        script = Path(__file__).resolve().parents[1] / "task_orchestrator.py"
        base = [sys.executable, str(script)]
        init = ["init", "--task-id", "context-test", "--goal", "context test",
                "--capability", "source analysis", "--risk", "low", "--allow", "lib/**",
                "--check", "python-tooling-tests", "--context", "lib/main.dart"]
        result = subprocess.run(base + init, cwd=self.root, text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, check=False, shell=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run(base + ["prepare", "--task-id", "context-test"], cwd=self.root,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=False, shell=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads((self.root / ".agent/tasks/context-test/task.json").read_text())
        package = record["context_package"]
        self.assertEqual(package["source_revision"], self.revision)
        self.assertEqual(package["source_context"][0]["path"], "lib/main.dart")
        self.assertIn("pinned", package["source_context"][0]["content"])


if __name__ == "__main__":
    unittest.main()
