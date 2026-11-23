import json
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.dispatcher import DispatcherError
from tools.task_orchestrator.local_dispatch_runner import run_fixture_dispatch
from tools.task_orchestrator.patch_artifacts import LocalPatchArtifactStore
from tools.task_orchestrator.provider_result_ingestion import (
    ProviderResultIngestionError,
    ingest_provider_result,
)
from tools.task_orchestrator.tests.test_agent_contract import envelope
from tools.task_orchestrator.tests.test_patch_pipeline import completed_result, patch_text


class FixtureToIngestionIntegrationTests(unittest.TestCase):
    def _prepare_task(self, root, env, result, patch):
        (root / "provider_result.json").write_text(
            json.dumps(result), encoding="utf-8"
        )
        (root / "provider_patch.diff").write_text(patch, encoding="utf-8")

    def test_fixture_dispatch_flows_into_artifact_ingestion_and_review_validation(self):
        env = envelope()
        patch = patch_text()
        result = completed_result(env, patch)

        # Exercise the same provider-neutral boundary used by the fixture runner.
        dispatch = run_fixture_dispatch(env, result)
        self.assertEqual(dispatch["status"], "completed")
        self.assertTrue(dispatch["result_validated"])
        self.assertEqual(dispatch["patch_validation"], "pending-artifact-validation")
        self.assertFalse(dispatch["patch_applied"])

        with tempfile.TemporaryDirectory() as directory:
            task_dir = Path(directory)
            self._prepare_task(task_dir, env, result, patch)

            ingestion = ingest_provider_result(task_dir, env)
            self.assertEqual(ingestion["status"], "validated_for_human_review")
            self.assertFalse(ingestion["applied"])
            self.assertEqual(ingestion["patch_ref"], dispatch["patch_ref"])
            self.assertTrue((task_dir / "agent_result.json").is_file())

            stored_result = json.loads(
                (task_dir / "agent_result.json").read_text(encoding="utf-8")
            )
            store = LocalPatchArtifactStore(task_dir / "patch-artifacts")
            review = store.validate_result_patch(stored_result, env)
            self.assertEqual(review["status"], "validated_for_human_review")
            self.assertFalse(review["applied"])
            self.assertEqual(
                review["patch_validation"]["changed_paths"],
                ["lib/routing_policy.dart"],
            )

    def test_dispatch_success_does_not_allow_tampered_patch_into_ingestion(self):
        env = envelope()
        patch = patch_text()
        result = completed_result(env, patch)
        dispatch = run_fixture_dispatch(env, result)
        self.assertTrue(dispatch["result_validated"])

        with tempfile.TemporaryDirectory() as directory:
            task_dir = Path(directory)
            self._prepare_task(task_dir, env, result, patch + "# tampered\\n")
            with self.assertRaises(ProviderResultIngestionError):
                ingest_provider_result(task_dir, env)
            self.assertFalse((task_dir / "agent_result.json").exists())

    def test_out_of_scope_fixture_result_is_rejected_before_ingestion(self):
        env = envelope()
        patch = patch_text().replace("lib/routing_policy.dart", "README.md")
        result = completed_result(env, patch)
        result["changed_paths"] = ["README.md"]
        dispatch = run_fixture_dispatch(env, result)
        # The dispatcher records adapter/contract rejection as a failed audit
        # record rather than throwing; failed records must never reach ingestion.
        self.assertEqual(dispatch["status"], "failed")
        self.assertFalse(dispatch["result_validated"])
        self.assertEqual(dispatch["patch_validation"], "not-run")
        self.assertFalse(dispatch["patch_applied"])

        with tempfile.TemporaryDirectory() as directory:
            task_dir = Path(directory)
            self._prepare_task(task_dir, env, result, patch)
            with self.assertRaises(ProviderResultIngestionError):
                ingest_provider_result(task_dir, env)
            self.assertFalse((task_dir / "agent_result.json").exists())


if __name__ == "__main__":
    unittest.main()
