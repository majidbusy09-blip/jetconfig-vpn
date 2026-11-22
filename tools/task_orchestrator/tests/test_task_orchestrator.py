from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "task_orchestrator.py"
REQUIRED = (
    "AGENTS.md",
    "docs/PROJECT_CONTEXT.md",
    "docs/CURRENT_STATUS.md",
    "docs/NEXT_STEPS.md",
    "docs/TASK_TEMPLATE.md",
    "docs/DEVELOPMENT_LOG.md",
)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, shell=False,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class OrchestratorIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        git(self.root, "init", "-b", "feature/test-task")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Orchestrator Test")
        for relative in REQUIRED:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"# fixture: {relative}\n", encoding="utf-8")
        tests_dir = self.root / "tools/task_orchestrator/tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_fixture.py").write_text(
            "import unittest\nclass FixtureTest(unittest.TestCase):\n"
            "    def test_ok(self): self.assertTrue(True)\n",
            encoding="utf-8",
        )
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "fixture baseline")
        self.task_id = "test-orchestrator"
        self.record = self.root / ".agent/tasks" / self.task_id / "task.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, shell=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def init_task(self, *checks: str) -> None:
        args = [
            "init", "--task-id", self.task_id, "--goal", "Exercise orchestrator",
            "--capability", "verification", "--risk", "low",
            "--allow", "docs/**",
        ]
        for check in checks or ("python-tooling-tests",):
            args.extend(["--check", check])
        self.cli(*args)

    def prepared_task(self) -> None:
        self.init_task()
        self.cli("prepare", "--task-id", self.task_id)

    def test_end_to_end_review_ready(self) -> None:
        self.prepared_task()
        self.cli("impact", "--task-id", self.task_id)
        self.cli("begin", "--task-id", self.task_id)
        (self.root / "docs/new-note.md").write_text("scoped change\n", encoding="utf-8")
        self.cli("validate-scope", "--task-id", self.task_id)
        self.cli("verify", "--task-id", self.task_id, "--profile", "python-tooling-tests")
        self.cli("finalize", "--task-id", self.task_id, "--reviewed-diff")
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["state"], "review_ready")
        self.assertEqual(record["scope_validation"]["status"], "passed")
        self.assertEqual(record["check_attempts"][-1]["status"], "passed")
        self.assertTrue((self.record.parent / "HANDOFF.md").is_file())

    def test_refuses_protected_main_branch(self) -> None:
        git(self.root, "branch", "-m", "main")
        self.init_task()
        self.cli("prepare", "--task-id", self.task_id, expected=2)

    def test_init_requires_clean_worktree(self) -> None:
        (self.root / "dirty.txt").write_text("not committed", encoding="utf-8")
        self.cli(
            "init", "--task-id", self.task_id, "--goal", "x", "--capability", "x",
            "--risk", "low", "--allow", "docs/**", "--check",
            "python-tooling-tests", expected=2,
        )
        self.assertFalse(self.record.exists())

    def test_prepare_rejects_preexisting_changes(self) -> None:
        self.init_task()
        (self.root / "unexpected.txt").write_text("dirty", encoding="utf-8")
        self.cli("prepare", "--task-id", self.task_id, expected=2)

    def test_scope_gate_rejects_unexpected_paths(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        (self.root / "outside.txt").write_text("out of scope", encoding="utf-8")
        self.cli("validate-scope", "--task-id", self.task_id, expected=2)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["scope_validation"]["status"], "failed")

    def test_begin_rejects_base_sha_drift(self) -> None:
        self.prepared_task()
        (self.root / "docs/base-drift.md").write_text("new commit", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "unexpected base movement")
        self.cli("begin", "--task-id", self.task_id, expected=2)

    def test_unknown_profile_is_rejected(self) -> None:
        self.cli(
            "init", "--task-id", self.task_id, "--goal", "x", "--capability", "x",
            "--risk", "low", "--allow", "docs/**", "--check", "arbitrary-shell",
            expected=2,
        )
        self.assertFalse(self.record.exists())


    def test_scope_gate_detects_content_changed_after_validation(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        target = self.root / "docs/new-note.md"
        target.write_text("first version\\n", encoding="utf-8")
        self.cli("validate-scope", "--task-id", self.task_id)
        target.write_text("changed after validation\\n", encoding="utf-8")
        self.cli("verify", "--task-id", self.task_id, "--profile", "python-tooling-tests")
        self.cli("finalize", "--task-id", self.task_id, "--reviewed-diff", expected=2)

    def test_failed_check_attempt_is_preserved_after_retry(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        failure_fixture = self.root / "tools/task_orchestrator/tests/test_fixture_failure.py"
        failure_fixture.write_text(
            "import unittest\\nclass FailureFixture(unittest.TestCase):\\n"
            "    def test_fail(self): self.assertTrue(False)\\n",
            encoding="utf-8",
        )
        self.cli("verify", "--task-id", self.task_id, "--profile", "python-tooling-tests", expected=2)
        failure_fixture.unlink()
        self.cli("verify", "--task-id", self.task_id, "--profile", "python-tooling-tests")
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(
            [item["status"] for item in record["check_attempts"]],
            ["failed", "passed"],
        )


    def test_refuses_remote_default_branch(self) -> None:
        git(self.root, "branch", "-m", "release")
        git(self.root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/release")
        self.init_task()
        self.cli("prepare", "--task-id", self.task_id, expected=2)

    def test_remote_credentials_are_not_recorded(self) -> None:
        git(self.root, "remote", "add", "origin",
            "https://user:top-secret@github.com/owner/repo.git?access_token=also-secret")
        self.init_task()
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["repository"]["origin"], "https://github.com/owner/repo.git")
        self.assertNotIn("top-secret", self.record.read_text(encoding="utf-8"))
        self.assertNotIn("also-secret", self.record.read_text(encoding="utf-8"))

    def test_prepare_rejects_missing_required_context(self) -> None:
        self.init_task()
        (self.root / "docs/TASK_TEMPLATE.md").unlink()
        self.cli("prepare", "--task-id", self.task_id, expected=2)

    def test_scope_validation_handles_rename_and_delete(self) -> None:
        old = self.root / "docs/old-note.md"
        old.write_text("baseline\\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "add scoped fixture")
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        git(self.root, "mv", "docs/old-note.md", "docs/renamed-note.md")
        (self.root / "docs/renamed-note.md").unlink()
        self.cli("validate-scope", "--task-id", self.task_id)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["scope_validation"]["status"], "passed")
        self.assertIn("docs/old-note.md", record["changed_paths"])

    def test_finalize_requires_explicit_diff_review(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        (self.root / "docs/new-note.md").write_text("scoped change\n", encoding="utf-8")
        self.cli("validate-scope", "--task-id", self.task_id)
        self.cli("verify", "--task-id", self.task_id, "--profile", "python-tooling-tests")
        self.cli("finalize", "--task-id", self.task_id, expected=2)


if __name__ == "__main__":
    unittest.main()
