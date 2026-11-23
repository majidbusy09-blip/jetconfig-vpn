from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace

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

    def test_accept_context_adds_only_explicit_suggested_paths(self) -> None:
        source = self.root / "lib/feature.dart"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("void feature() {}\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "add context source fixture")
        self.cli(
            "init", "--task-id", self.task_id, "--goal", "Select source context",
            "--capability", "context selection", "--risk", "low",
            "--allow", "lib/**", "--check", "python-tooling-tests",
        )
        self.cli("prepare", "--task-id", self.task_id)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        base = record["repository"]["base_sha"]
        blob = git(self.root, "rev-parse", f"{base}:lib/feature.dart")
        suggestions = self.record.parent / "context_suggestions_fixture.json"
        suggestions.write_text(json.dumps({
            "schema_version": 1, "task_id": self.task_id,
            "source_revision": base,
            "suggestions": [{"path": "lib/feature.dart", "git_blob_sha": blob}],
        }), encoding="utf-8")
        relative_suggestions = suggestions.relative_to(self.root).as_posix()
        self.cli(
            "accept-context", "--task-id", self.task_id,
            "--suggestions", relative_suggestions, "--path", "lib/feature.dart",
        )
        updated = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(updated["context_paths"], ["lib/feature.dart"])
        self.assertEqual(updated["context_package"]["source_context"][0]["path"], "lib/feature.dart")
        self.assertEqual(updated["scope"]["allowed"], ["lib/**"])
        self.assertEqual(updated["context_selection"]["accepted_paths"], ["lib/feature.dart"])

    def test_accept_context_rejects_paths_not_in_suggestion_artifact(self) -> None:
        source = self.root / "lib/feature.dart"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("void feature() {}\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "add context source fixture")
        self.cli(
            "init", "--task-id", self.task_id, "--goal", "Select source context",
            "--capability", "context selection", "--risk", "low",
            "--allow", "lib/**", "--check", "python-tooling-tests",
        )
        self.cli("prepare", "--task-id", self.task_id)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        suggestions = self.record.parent / "context_suggestions_fixture.json"
        suggestions.write_text(json.dumps({
            "schema_version": 1, "task_id": self.task_id,
            "source_revision": record["repository"]["base_sha"],
            "suggestions": [{"path": "lib/feature.dart", "git_blob_sha":
                git(self.root, "rev-parse", f"{record['repository']['base_sha']}:lib/feature.dart")}],
        }), encoding="utf-8")
        self.cli(
            "accept-context", "--task-id", self.task_id,
            "--suggestions", suggestions.relative_to(self.root).as_posix(),
            "--path", "lib/not-suggested.dart", expected=2,
        )
        unchanged = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(unchanged["context_paths"], [])

    def test_accept_context_rejects_stale_suggestion_fingerprint(self) -> None:
        source = self.root / "lib/feature.dart"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("void feature() {}\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "add context source fixture")
        self.cli(
            "init", "--task-id", self.task_id, "--goal", "Select source context",
            "--capability", "context selection", "--risk", "low",
            "--allow", "lib/**", "--check", "python-tooling-tests",
        )
        self.cli("prepare", "--task-id", self.task_id)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        suggestions = self.record.parent / "context_suggestions_fixture.json"
        suggestions.write_text(json.dumps({
            "schema_version": 1, "task_id": self.task_id,
            "source_revision": record["repository"]["base_sha"],
            "suggestions": [{"path": "lib/feature.dart", "git_blob_sha": "0" * 40}],
        }), encoding="utf-8")
        self.cli(
            "accept-context", "--task-id", self.task_id,
            "--suggestions", suggestions.relative_to(self.root).as_posix(),
            "--path", "lib/feature.dart", expected=2,
        )
        unchanged = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(unchanged["context_paths"], [])

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
        handoff_relative = (self.record.parent / "HANDOFF.md").relative_to(self.root).as_posix()
        self.assertIn(handoff_relative, record["changed_paths"])
        self.assertIn(handoff_relative, record["final_diff"]["untracked_paths"])

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

    def test_repository_wide_scope_requires_high_risk_reason(self) -> None:
        self.cli(
            "init", "--task-id", self.task_id, "--goal", "x", "--capability", "x",
            "--risk", "low", "--allow", "**", "--check", "python-tooling-tests",
            expected=2,
        )
        self.assertFalse(self.record.exists())
        self.cli(
            "init", "--task-id", self.task_id, "--goal", "x", "--capability", "x",
            "--risk", "high", "--scope-reason", "repository-wide migration",
            "--allow", "**", "--check", "python-tooling-tests",
        )
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["scope"]["reason"], "repository-wide migration")

    def test_malformed_task_record_is_rejected(self) -> None:
        self.init_task()
        self.record.write_text("[]\\n", encoding="utf-8")
        self.cli("prepare", "--task-id", self.task_id, expected=2)

    def test_blank_goal_is_rejected(self) -> None:
        self.cli(
            "init", "--task-id", self.task_id, "--goal", "", "--capability", "x",
            "--risk", "low", "--allow", "docs/**", "--check", "python-tooling-tests",
            expected=2,
        )
        self.assertFalse(self.record.exists())

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
        deleted = self.root / "docs/delete-note.md"
        old.write_text("rename baseline\\n", encoding="utf-8")
        deleted.write_text("delete baseline\\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "add scoped fixtures")
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        git(self.root, "mv", "docs/old-note.md", "docs/renamed-note.md")
        deleted.unlink()
        self.cli("validate-scope", "--task-id", self.task_id)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["scope_validation"]["status"], "passed")
        self.assertIn("docs/old-note.md", record["changed_paths"])
        self.assertIn("docs/renamed-note.md", record["changed_paths"])
        self.assertIn("docs/delete-note.md", record["changed_paths"])

    def test_finalize_requires_explicit_diff_review(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        (self.root / "docs/new-note.md").write_text("scoped change\n", encoding="utf-8")
        self.cli("validate-scope", "--task-id", self.task_id)
        self.cli("verify", "--task-id", self.task_id, "--profile", "python-tooling-tests")
        self.cli("finalize", "--task-id", self.task_id, expected=2)


    def test_tracked_symlink_fingerprint_does_not_read_target(self) -> None:
        external = Path(self.temp.name).parent / (Path(self.temp.name).name + "-outside-secret")
        external.write_text("do-not-read-this-content", encoding="utf-8")
        try:
            link = self.root / "docs/external-link"
            link.symlink_to(external)
            git(self.root, "add", "docs/external-link")
            git(self.root, "commit", "-m", "add symlink fixture")
            spec = importlib.util.spec_from_file_location("task_orchestrator_under_test", SCRIPT)
            module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(module)
            actual = module.file_fingerprints(self.root, ["docs/**"])["docs/external-link"]
            expected = hashlib.sha256(os.readlink(link).encode("utf-8")).hexdigest()
            self.assertEqual(actual, expected)
            self.assertNotEqual(actual, hashlib.sha256(external.read_bytes()).hexdigest())
        finally:
            external.unlink(missing_ok=True)

    def test_timeout_is_recorded_as_failure_without_bytes_type_error(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        spec = importlib.util.spec_from_file_location("task_orchestrator_timeout_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        old_cwd = Path.cwd()
        try:
            os.chdir(self.root)
            module.PROFILES["python-tooling-tests"] = {
                "argv": [sys.executable, "-c", "import time; time.sleep(2)"],
                "timeout": 0.01,
            }
            with self.assertRaises(module.TaskError):
                module.command_verify(Namespace(task_id=self.task_id, profile="python-tooling-tests"))
        finally:
            os.chdir(old_cwd)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        attempt = record["check_attempts"][-1]
        self.assertEqual(attempt["status"], "failed")
        self.assertEqual(attempt["exit_code"], 124)
        self.assertEqual(len(attempt["output_sha256"]), 64)


    def test_unexpected_file_inside_task_directory_is_not_metadata_exempt(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        extra = self.record.parent / "unexpected.txt"
        extra.write_text("not an orchestrator-owned file", encoding="utf-8")
        self.cli("validate-scope", "--task-id", self.task_id, expected=2)

    def test_operations_reject_branch_switch_after_prepare(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        git(self.root, "switch", "-c", "other/task-branch")
        self.cli("verify", "--task-id", self.task_id, "--profile", "python-tooling-tests", expected=2)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["check_attempts"], [])

    def test_operations_reject_detached_head_after_prepare(self) -> None:
        self.prepared_task()
        git(self.root, "checkout", "--detach")
        self.cli("begin", "--task-id", self.task_id, expected=2)

    def test_verify_rejects_source_changes_during_check(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        target = self.root / "docs/new-note.md"
        target.write_text("before check\\n", encoding="utf-8")
        spec = importlib.util.spec_from_file_location("task_orchestrator_race_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        old_cwd = Path.cwd()
        try:
            os.chdir(self.root)
            module.PROFILES["python-tooling-tests"] = {
                "argv": [
                    sys.executable, "-c",
                    "from pathlib import Path; Path('docs/new-note.md').write_text('changed during check\\n')",
                ],
                "timeout": 10,
            }
            with self.assertRaises(module.TaskError):
                module.command_verify(
                    Namespace(task_id=self.task_id, profile="python-tooling-tests")
                )
        finally:
            os.chdir(old_cwd)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        attempt = record["check_attempts"][-1]
        self.assertEqual(attempt["status"], "failed")
        self.assertEqual(attempt["exit_code"], 125)
        self.assertFalse(attempt["source_stable_during_check"])
        self.assertNotEqual(
            attempt["verification_input_path_fingerprints"],
            attempt["verified_path_fingerprints"],
        )

    def test_finalize_rejects_latest_failed_attempt_even_if_older_attempt_passed(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        target = self.root / "docs/new-note.md"
        target.write_text("implementation\\n", encoding="utf-8")
        self.cli("validate-scope", "--task-id", self.task_id)
        self.cli("verify", "--task-id", self.task_id, "--profile", "python-tooling-tests")
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["check_attempts"][-1]["status"], "passed")
        failed_attempt = dict(record["check_attempts"][-1])
        failed_attempt.update({
            "status": "failed",
            "exit_code": 1,
            "output_sha256": "simulated-later-failure",
            "finished_at": "2099-01-01T00:00:00+00:00",
        })
        record["check_attempts"].append(failed_attempt)
        self.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        self.cli("finalize", "--task-id", self.task_id, "--reviewed-diff", expected=2)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["state"], "verification")
        self.assertEqual(record["check_attempts"][-1]["status"], "failed")

    def test_finalize_rejects_checks_stale_after_scope_revalidation(self) -> None:
        self.prepared_task()
        self.cli("begin", "--task-id", self.task_id)
        target = self.root / "docs/new-note.md"
        target.write_text("first implementation\\n", encoding="utf-8")
        self.cli("validate-scope", "--task-id", self.task_id)
        self.cli("verify", "--task-id", self.task_id, "--profile", "python-tooling-tests")
        target.write_text("changed after successful verification\\n", encoding="utf-8")
        self.cli("validate-scope", "--task-id", self.task_id)
        self.cli("finalize", "--task-id", self.task_id, "--reviewed-diff", expected=2)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["check_attempts"][-1]["status"], "passed")
        self.cli("verify", "--task-id", self.task_id, "--profile", "python-tooling-tests")
        self.cli("finalize", "--task-id", self.task_id, "--reviewed-diff")
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["state"], "review_ready")

if __name__ == "__main__":
    unittest.main()
