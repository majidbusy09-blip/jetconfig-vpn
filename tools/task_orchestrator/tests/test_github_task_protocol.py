import copy
import json
import unittest
from pathlib import Path

from tools.task_orchestrator.github_task_protocol import (
    GitHubTaskError, validate_issue_body, validate_task_payload,
)

JET_REPOSITORY = {
    "id": 1349356614,
    "full_name": "majidbusy09-blip/jetconfig-vpn",
    "html_url": "https://github.com/majidbusy09-blip/jetconfig-vpn",
    "default_branch": "main",
}
V1_PAYLOAD = {
    "schema_version": 1, "task_id": "smart-server-health",
    "goal": "Improve server health selection and report measured behavior.",
    "capability": "implementation", "risk": "medium", "assigned_agent": "any",
    "allow": ["lib/**", "test/**"], "exclude": ["lib/secrets.dart"],
    "scope_reason": "Keep the task within application logic and tests.",
    "verification_profiles": ["flutter-analysis", "flutter-tests"],
}
V2_PAYLOAD = {
    **{key: value for key, value in V1_PAYLOAD.items() if key != "schema_version"},
    "schema_version": 2,
    "project_binding": {
        "project_id": "sample-project",
        "repository_id": "1349356614",
        "repository_full_name": "majidbusy09-blip/jetconfig-vpn",
        "default_branch": "main",
        "manifest_schema_version": 1,
        "manifest_sha256": "a" * 64,
    },
}


def issue_body(payload=V1_PAYLOAD):
    fence = chr(96) * 3
    marker = "<!-- jet-agent-task:v2 -->" if payload["schema_version"] == 2 else "<!-- jet-agent-task:v1 -->"
    return marker + "\n\n" + fence + "json\n" + json.dumps(payload) + "\n" + fence + "\n"


class GitHubTaskProtocolTests(unittest.TestCase):
    def test_accepts_v1_only_for_exact_legacy_jet_vpn_identity(self):
        result = validate_issue_body(
            issue_body(), repository_metadata=JET_REPOSITORY, allow_legacy_jet_vpn=True
        )
        self.assertEqual(result["task_id"], "smart-server-health")
        self.assertEqual(result["assigned_agent"], "any")
        with self.assertRaises(GitHubTaskError):
            validate_issue_body(issue_body())
        other = dict(JET_REPOSITORY, id=123, full_name="other/repository",
                     html_url="https://github.com/other/repository")
        with self.assertRaises(GitHubTaskError):
            validate_issue_body(issue_body(), repository_metadata=other, allow_legacy_jet_vpn=True)

    def test_accepts_well_formed_v2_project_binding(self):
        result = validate_issue_body(issue_body(V2_PAYLOAD))
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["project_binding"]["repository_id"], "1349356614")

    def test_rejects_malformed_v2_identity_fields(self):
        for key, value in (
            ("project_id", "Not a project"),
            ("repository_id", "owner/repository"),
            ("repository_full_name", "not-canonical"),
            ("default_branch", ""),
            ("manifest_schema_version", True),
            ("manifest_sha256", "bad"),
        ):
            bad = copy.deepcopy(V2_PAYLOAD)
            bad["project_binding"][key] = value
            with self.subTest(key=key), self.assertRaises(GitHubTaskError):
                validate_task_payload(bad)

    def test_rejects_duplicate_json_keys(self):
        raw = '{"schema_version":1,"schema_version":1}'
        fence = chr(96) * 3
        with self.assertRaises(GitHubTaskError):
            validate_issue_body(
                "<!-- jet-agent-task:v1 -->\n" + fence + "json\n" + raw + "\n" + fence,
                repository_metadata=JET_REPOSITORY, allow_legacy_jet_vpn=True,
            )

    def test_requires_exactly_one_marker_and_matching_version(self):
        with self.assertRaises(GitHubTaskError):
            validate_issue_body("no structured task here")
        with self.assertRaises(GitHubTaskError):
            validate_issue_body(issue_body() + issue_body(),
                                repository_metadata=JET_REPOSITORY, allow_legacy_jet_vpn=True)
        mismatch = issue_body(V1_PAYLOAD).replace("v1", "v2")
        with self.assertRaises(GitHubTaskError):
            validate_issue_body(mismatch, repository_metadata=JET_REPOSITORY, allow_legacy_jet_vpn=True)

    def test_rejects_path_traversal_and_protected_paths(self):
        for path in ("../lib/main.dart", "/etc/passwd", "lib/../secrets",
                     ".agent/tasks/**", ".github/workflows/**"):
            bad = dict(V1_PAYLOAD, allow=[path])
            with self.subTest(path=path), self.assertRaises(GitHubTaskError):
                validate_task_payload(
                    bad, repository_metadata=JET_REPOSITORY, allow_legacy_jet_vpn=True
                )

    def test_rejects_unknown_agent_capability_and_profile(self):
        for key, value in (
            ("assigned_agent", "unknown-agent"), ("capability", "deploy"),
            ("verification_profiles", ["arbitrary-shell"]),
        ):
            bad = dict(V1_PAYLOAD, **{key: value})
            with self.subTest(key=key), self.assertRaises(GitHubTaskError):
                validate_task_payload(
                    bad, repository_metadata=JET_REPOSITORY, allow_legacy_jet_vpn=True
                )

    def test_rejects_unknown_fields_and_oversized_goal(self):
        with self.assertRaises(GitHubTaskError):
            validate_task_payload(
                dict(V1_PAYLOAD, shell="rm -rf"),
                repository_metadata=JET_REPOSITORY, allow_legacy_jet_vpn=True,
            )
        with self.assertRaises(GitHubTaskError):
            validate_task_payload(
                dict(V1_PAYLOAD, goal="x" * 8001),
                repository_metadata=JET_REPOSITORY, allow_legacy_jet_vpn=True,
            )


if __name__ == "__main__":
    unittest.main()
