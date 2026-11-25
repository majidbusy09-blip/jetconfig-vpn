import json
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.local_dispatch_runner import (
    LocalDispatchRunnerError,
    main,
    run_fixture_dispatch,
)
from tools.task_orchestrator.tests.test_agent_contract import envelope, result_for
from tools.task_orchestrator.project_artifact_namespace import audit_record_path


class LocalDispatchRunnerTests(unittest.TestCase):
    def test_fixture_dispatch_validates_and_never_applies_patch(self):
        record = run_fixture_dispatch(envelope(), result_for())
        self.assertEqual(record["status"], "completed")
        self.assertTrue(record["result_validated"])
        self.assertFalse(record["patch_applied"])

    def test_cli_writes_new_audit_record(self):
        env = envelope()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_path = root / "agent_input.json"
            result_path = root / "fixture_result.json"
            output_path = root / "dispatch_audit.json"
            env_path.write_text(json.dumps(env), encoding="utf-8")
            result_path.write_text(json.dumps(result_for(env)), encoding="utf-8")
            code = main([
                "--envelope-file", str(env_path),
                "--fixture-result-file", str(result_path),
                "--output", str(output_path),
            ])
            self.assertEqual(code, 0)
            record = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(record["task_id"], env["task_id"])
            self.assertFalse(record["patch_applied"])

    def test_cli_refuses_to_overwrite_existing_audit(self):
        env = envelope()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_path = root / "agent_input.json"
            result_path = root / "fixture_result.json"
            output_path = root / "dispatch_audit.json"
            env_path.write_text(json.dumps(env), encoding="utf-8")
            result_path.write_text(json.dumps(result_for(env)), encoding="utf-8")
            output_path.write_text("preserve", encoding="utf-8")
            self.assertEqual(main([
                "--envelope-file", str(env_path),
                "--fixture-result-file", str(result_path),
                "--output", str(output_path),
            ]), 2)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "preserve")

    def test_rejects_symlink_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.json"
            link = root / "link.json"
            target.write_text("{}", encoding="utf-8")
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink creation unavailable")
            from tools.task_orchestrator.local_dispatch_runner import _read_object
            with self.assertRaises(LocalDispatchRunnerError):
                _read_object(str(link))

    def test_v2_dispatch_audit_is_written_under_project_and_revision_namespace(self):
        env = envelope()
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
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs/generated").mkdir(parents=True)
            env_path = root / "agent_input.json"
            result_path = root / "fixture_result.json"
            env_path.write_text(json.dumps(env), encoding="utf-8")
            result_path.write_text(json.dumps(result_for(env)), encoding="utf-8")
            code = main([
                "--envelope-file", str(env_path),
                "--fixture-result-file", str(result_path),
                "--repository-root", str(root),
            ])
            self.assertEqual(code, 0)
            expected = root / audit_record_path(
                "dispatch-audit.json", project_binding=binding,
                source_revision=env["repository"]["base_sha"],
            )
            self.assertTrue(expected.is_file())
            self.assertEqual(json.loads(expected.read_text(encoding="utf-8"))["task_id"], env["task_id"])

    def test_v2_dispatch_rejects_unscoped_audit_output_override(self):
        env = envelope()
        env["project_binding"] = {
            "project_id": "jet-vpn-android", "repository_id": "1349356614",
            "repository_full_name": "majidbusy09-blip/jetconfig-vpn", "default_branch": "main",
            "manifest_schema_version": 1, "manifest_sha256": "a" * 64,
            "base_sha": env["repository"]["base_sha"],
        }
        env["memory_manifest"] = {
            "version": 1,
            "required_documents": [item["path"] for item in env["project_context"]],
            "max_total_bytes": 512000,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs/generated").mkdir(parents=True)
            env_path = root / "agent_input.json"
            result_path = root / "fixture_result.json"
            env_path.write_text(json.dumps(env), encoding="utf-8")
            result_path.write_text(json.dumps(result_for(env)), encoding="utf-8")
            self.assertEqual(main([
                "--envelope-file", str(env_path),
                "--fixture-result-file", str(result_path),
                "--repository-root", str(root),
                "--output", str(root / "dispatch_audit.json"),
            ]), 2)
            self.assertFalse((root / "dispatch_audit.json").exists())


if __name__ == "__main__":
    unittest.main()
