import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.provider_result_ingestion import (
    ProviderResultIngestionError,
    ingest_provider_result,
)
from tools.task_orchestrator.tests.test_patch_pipeline import completed_result, patch_text
from tools.task_orchestrator.tests.test_agent_contract import envelope


class ProviderResultIngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.task_dir = Path(self.temp.name)
        self.envelope = envelope()
        self.patch = patch_text()
        self.result = completed_result(self.envelope, self.patch)
        (self.task_dir / "provider_result.json").write_text(
            json.dumps(self.result), encoding="utf-8"
        )
        (self.task_dir / "provider_patch.diff").write_text(self.patch, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_ingests_exact_patch_and_validates_for_human_review(self):
        outcome = ingest_provider_result(self.task_dir, self.envelope)
        self.assertEqual(outcome["status"], "validated_for_human_review")
        self.assertFalse(outcome["applied"])
        self.assertEqual(outcome["patch_ref"], "artifact:sha256:" + hashlib.sha256(self.patch.encode()).hexdigest())
        self.assertTrue((self.task_dir / "agent_result.json").is_file())
        self.assertTrue((self.task_dir / "patch-artifacts" / (hashlib.sha256(self.patch.encode()).hexdigest() + ".patch")).is_file())

    def test_rejects_patch_digest_mismatch_without_result_file(self):
        (self.task_dir / "provider_patch.diff").write_text(self.patch + "# tampered", encoding="utf-8")
        with self.assertRaises(ProviderResultIngestionError):
            ingest_provider_result(self.task_dir, self.envelope)
        self.assertFalse((self.task_dir / "agent_result.json").exists())

    def test_rejects_existing_result_instead_of_overwriting(self):
        (self.task_dir / "agent_result.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(ProviderResultIngestionError):
            ingest_provider_result(self.task_dir, self.envelope)
        self.assertEqual((self.task_dir / "agent_result.json").read_text(encoding="utf-8"), "{}")

    def test_rejects_symlinked_patch_input(self):
        original = self.task_dir / "provider_patch.diff"
        target = self.task_dir / "real.patch"
        original.rename(target)
        try:
            original.symlink_to(target)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        with self.assertRaises(ProviderResultIngestionError):
            ingest_provider_result(self.task_dir, self.envelope)

    def test_rejects_output_path_escape(self):
        with self.assertRaises(ProviderResultIngestionError):
            ingest_provider_result(self.task_dir, self.envelope, result_path="../agent_result.json")


    def test_v2_ingestion_persists_patch_under_project_manifest_and_source_namespace(self):
        env = dict(self.envelope)
        env["repository"] = dict(self.envelope["repository"])
        binding = {
            "project_id": "jet-vpn-android",
            "repository_id": "1349356614",
            "repository_full_name": "majidbusy09-blip/jetconfig-vpn",
            "default_branch": "main",
            "manifest_schema_version": 1,
            "manifest_sha256": "a" * 64,
            "base_sha": env["repository"]["base_sha"],
        }
        env["project_binding"] = binding
        env["memory_manifest"] = {
            "version": 1,
            "required_documents": [item["path"] for item in env["project_context"]],
            "max_total_bytes": 512000,
        }
        result = completed_result(env, self.patch)
        (self.task_dir / "provider_result.json").write_text(json.dumps(result), encoding="utf-8")
        outcome = ingest_provider_result(
            self.task_dir, env, project_binding=binding,
            source_revision=env["repository"]["base_sha"],
        )
        expected = (
            "patch-artifacts/projects/jet-vpn-android/1349356614/" + "a" * 64 + "/"
            + env["repository"]["base_sha"] + "/patches"
        )
        self.assertEqual(outcome["artifact_directory"], expected)
        self.assertEqual(outcome["status"], "validated_for_human_review")
        self.assertFalse(outcome["applied"])

    def test_v2_ingestion_rejects_source_revision_mismatch(self):
        env = dict(self.envelope)
        env["repository"] = dict(self.envelope["repository"])
        binding = {
            "project_id": "jet-vpn-android",
            "repository_id": "1349356614",
            "repository_full_name": "majidbusy09-blip/jetconfig-vpn",
            "default_branch": "main",
            "manifest_schema_version": 1,
            "manifest_sha256": "a" * 64,
            "base_sha": env["repository"]["base_sha"],
        }
        env["project_binding"] = binding
        env["memory_manifest"] = {
            "version": 1,
            "required_documents": [item["path"] for item in env["project_context"]],
            "max_total_bytes": 512000,
        }
        result = completed_result(env, self.patch)
        (self.task_dir / "provider_result.json").write_text(json.dumps(result), encoding="utf-8")
        with self.assertRaises(ProviderResultIngestionError):
            ingest_provider_result(
                self.task_dir, env, project_binding=binding, source_revision="e" * 40,
            )
        self.assertFalse((self.task_dir / "agent_result.json").exists())


if __name__ == "__main__":
    unittest.main()
