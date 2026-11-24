"""Integration tests for the read-only review command wiring."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.task_orchestrator import patch_review_command as command
from tools.task_orchestrator.patch_artifacts import LocalPatchArtifactStore
from tools.task_orchestrator.provider_result_ingestion import ingest_provider_result
from tools.task_orchestrator.tests.test_patch_review_gate import (
    BASE, HEAD, LOCK, NOW, REPO, TASK, fixtures,
)
from tools.task_orchestrator.tests.test_patch_pipeline import completed_result, patch_text


class PatchReviewCommandIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.task_dir = self.root / ".agent" / "tasks" / TASK
        self.artifact_dir = self.task_dir / "patch-artifacts"
        self.artifact_dir.mkdir(parents=True)
        self.record, self.envelope, self.issue, self.lease = fixtures()
        self.record["schema_version"] = 1
        self.patch = patch_text()
        self.result = completed_result(self.envelope, self.patch)
        (self.task_dir / "agent_input.json").write_text(
            json.dumps(self.envelope), encoding="utf-8"
        )
        (self.task_dir / "agent_result.json").write_text(
            json.dumps(self.result), encoding="utf-8"
        )
        (self.task_dir / "task.json").write_text(
            json.dumps(self.record), encoding="utf-8"
        )
        LocalPatchArtifactStore(self.artifact_dir).store_patch(self.patch)
        self.record_path = self.task_dir / "task.json"

    def tearDown(self):
        self.temp.cleanup()

    def _run(self, issue=None, lease=None, lock_commit=LOCK):
        with (
            patch.object(command.orchestrator, "repository_root", return_value=self.root),
            patch.object(command.orchestrator, "load_record",
                         return_value=(self.record, self.record_path)),
            patch.object(command.orchestrator, "run_git", side_effect=lambda _root, *args, **kwargs: HEAD if args[:2] == ("rev-parse", "HEAD") else "https://github.com/" + REPO + ".git"),
            patch.object(command.orchestrator, "safe_remote_identity",
                         return_value="https://github.com/" + REPO + ".git"),
            patch.object(command.orchestrator, "current_branch", return_value="agent/" + TASK),
            patch.object(command.orchestrator, "status_paths", return_value=[]),
            patch.object(command, "_base_is_ancestor", return_value=True),
            patch.object(command, "api_get", return_value=issue or self.issue),
            patch.object(command, "_read_current_lease",
                         return_value=(lease or self.lease, lock_commit)),
        ):
            return command.review_task_patch(
                TASK, token="read-only-test-token", now=NOW
            )

    def test_live_observation_adapters_reach_review_gate_without_applying_patch(self):
        result = self._run()
        self.assertEqual(result["status"], "ready_for_human_review")
        self.assertFalse(result["applied"])
        self.assertEqual(result["patch_ref"], self.result["patch_ref"])
        self.assertTrue(all(result["authorization"].values()))

    def test_provider_ingestion_flows_directly_into_live_review_command(self):
        # Start with provider-neutral files; ingestion must create the exact
        # agent_result.json that the live review command consumes.
        (self.task_dir / "agent_result.json").unlink()
        (self.task_dir / "provider_result.json").write_text(
            json.dumps(self.result), encoding="utf-8"
        )
        (self.task_dir / "provider_patch.diff").write_text(
            self.patch, encoding="utf-8"
        )

        ingestion = ingest_provider_result(self.task_dir, self.envelope)
        self.assertEqual(ingestion["status"], "validated_for_human_review")
        self.assertFalse(ingestion["applied"])
        self.assertEqual(ingestion["patch_ref"], self.result["patch_ref"])

        review = self._run()
        self.assertEqual(review["status"], "ready_for_human_review")
        self.assertFalse(review["applied"])
        self.assertEqual(review["patch_ref"], ingestion["patch_ref"])
        self.assertTrue(all(review["authorization"].values()))

    def test_current_issue_mismatch_fails_closed_before_review(self):
        changed_issue = dict(self.issue, state="closed")
        with self.assertRaises(command.PatchReviewCommandError):
            self._run(issue=changed_issue)


if __name__ == "__main__":
    unittest.main()
