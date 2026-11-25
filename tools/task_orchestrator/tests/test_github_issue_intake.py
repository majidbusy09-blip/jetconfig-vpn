import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.github_issue_intake import IntakeError, build_intake, load_project_configuration
from tools.task_orchestrator.project_registry import manifest_digest

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "docs/PROJECT_MANIFEST_SCHEMA.json").read_text(encoding="utf-8"))
JET_MANIFEST = copy.deepcopy(SCHEMA["examples"][0])
JET_MANIFEST["lifecycle"] = "active"
JET_REPOSITORY = {
    "id": 1349356614,
    "full_name": "majidbusy09-blip/jetconfig-vpn",
    "html_url": "https://github.com/majidbusy09-blip/jetconfig-vpn",
    "default_branch": "main",
}
V1_PAYLOAD = {
    "schema_version": 1, "task_id": "sample-task",
    "goal": "Improve a bounded feature and verify it.",
    "capability": "implementation", "risk": "low", "assigned_agent": "any",
    "allow": ["lib/**"], "exclude": ["lib/secrets.dart"],
    "scope_reason": "Keep the change within application code.",
    "verification_profiles": ["flutter-analysis"],
}


def task_body(payload):
    fence = chr(96) * 3
    version = payload["schema_version"]
    return f"<!-- jet-agent-task:v{version} -->\n" + fence + "json\n" + json.dumps(payload) + "\n" + fence


def event(payload=V1_PAYLOAD, **issue_overrides):
    issue = {
        "number": 42, "title": "Sample task", "body": task_body(payload), "state": "open",
        "html_url": "https://github.com/majidbusy09-blip/jetconfig-vpn/issues/42",
        "labels": [{"name": "agent-task"}],
    }
    issue.update(issue_overrides)
    return {"action": "opened", "repository": dict(JET_REPOSITORY), "issue": issue}


def v2_payload(manifest=None):
    manifest = copy.deepcopy(manifest or JET_MANIFEST)
    repository = manifest["repository"]
    return {
        **{key: value for key, value in V1_PAYLOAD.items() if key != "schema_version"},
        "schema_version": 2,
        "project_binding": {
            "project_id": manifest["project_id"],
            "repository_id": repository["repository_id"],
            "repository_full_name": repository["full_name"],
            "default_branch": repository["default_branch"],
            "manifest_schema_version": manifest["schema_version"],
            "manifest_sha256": manifest_digest(manifest),
        },
    }


class GitHubIssueIntakeTests(unittest.TestCase):
    def test_builds_validated_non_executing_legacy_artifact(self):
        result = build_intake(event())
        self.assertEqual(result["task"]["task_id"], "sample-task")
        self.assertEqual(result["intake_schema"], 2)
        self.assertEqual(result["execution"]["status"], "validated-awaiting-claim")
        self.assertFalse(result["execution"]["agent_dispatched"])
        self.assertFalse(result["execution"]["lease_claimed"])

    def test_rejects_v1_for_any_repository_other_than_legacy_jet_vpn(self):
        bad = event()
        bad["repository"] = {
            "id": 123, "full_name": "other/repository",
            "html_url": "https://github.com/other/repository", "default_branch": "main",
        }
        with self.assertRaises(IntakeError):
            build_intake(bad)

    def test_accepts_v2_only_when_binding_manifest_and_live_metadata_match(self):
        payload = v2_payload()
        result = build_intake(
            event(payload), project_schema=SCHEMA, project_manifests=[JET_MANIFEST]
        )
        self.assertEqual(result["task"]["schema_version"], 2)
        self.assertEqual(result["project_binding"], payload["project_binding"])
        self.assertFalse(result["execution"]["model_called"])

    def test_rejects_v2_stale_digest_mismatched_repo_and_inactive_manifest(self):
        payload = v2_payload()
        payload["project_binding"]["manifest_sha256"] = "b" * 64
        with self.assertRaises(IntakeError):
            build_intake(event(payload), project_schema=SCHEMA, project_manifests=[JET_MANIFEST])

        payload = v2_payload()
        bad_event = event(payload)
        bad_event["repository"]["id"] = 99
        with self.assertRaises(IntakeError):
            build_intake(bad_event, project_schema=SCHEMA, project_manifests=[JET_MANIFEST])

        inactive = copy.deepcopy(JET_MANIFEST)
        inactive["lifecycle"] = "registered"
        with self.assertRaises(IntakeError):
            build_intake(
                event(v2_payload(inactive)), project_schema=SCHEMA, project_manifests=[inactive]
            )

    def test_rejects_missing_label_closed_issue_and_pull_request(self):
        for overrides in (
            {"labels": []}, {"state": "closed"},
            {"pull_request": {"url": "https://api.github.com/pulls/42"}},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(IntakeError):
                build_intake(event(**overrides))

    def test_rejects_untrusted_or_ineligible_event(self):
        edited = build_intake(dict(event(), action="edited"))
        self.assertEqual(edited["task"]["task_id"], "sample-task")
        with self.assertRaises(IntakeError):
            build_intake({"action": "opened", "issue": {}, "repository": {}})

    def test_rejects_malformed_manifest_identity_as_intake_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "docs/projects/bad-project").mkdir(parents=True)
            (root / "docs/PROJECT_MANIFEST_SCHEMA.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
            bad = copy.deepcopy(JET_MANIFEST)
            bad["project_id"] = []
            (root / "docs/projects/bad-project/manifest.json").write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(IntakeError):
                load_project_configuration(root)

    def test_rejects_invalid_task_payload(self):
        bad = event(body="plain text")
        with self.assertRaises(IntakeError):
            build_intake(bad)


if __name__ == "__main__":
    unittest.main()
