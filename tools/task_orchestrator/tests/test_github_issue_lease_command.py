import json
import unittest
from unittest.mock import patch

from tools.task_orchestrator.github_issue_lease_command import (
    IssueLeaseCommandError, build_issue_lease_request, execute_issue_lease_command,
    parse_lease_comment,
)

CLAIM_A = "a" * 16
CLAIM_B = "b" * 16
BASE = "c" * 40
JET_REPOSITORY = "majidbusy09-blip/jetconfig-vpn"
JET_METADATA = {"id": 1349356614, "full_name": JET_REPOSITORY, "html_url": "https://github.com/" + JET_REPOSITORY, "default_branch": "main"}


def issue_event(comment_body, *, assigned_agent="any", association="OWNER"):
    payload = {
        "schema_version": 1,
        "task_id": "sample-task",
        "goal": "A bounded test task.",
        "capability": "documentation",
        "risk": "low",
        "assigned_agent": assigned_agent,
        "allow": ["docs/**"],
        "exclude": [],
        "scope_reason": "Documentation-only validation.",
        "verification_profiles": ["python-tooling-tests"],
    }
    body = "<!-- jet-agent-task:v1 -->\n\n" + "\x60\x60\x60json\n" + json.dumps(payload) + "\n\x60\x60\x60"
    return {
        "action": "created",
        "repository": dict(JET_METADATA),
        "issue": {
            "number": 42,
            "state": "open",
            "title": "[JET-AGENT] Sample task",
            "body": body,
            "html_url": "https://github.com/majidbusy09-blip/jetconfig-vpn/issues/42",
            "labels": [{"name": "agent-task"}],
        },
        "comment": {
            "body": comment_body,
            "author_association": association,
            "user": {"login": "owner"},
        },
    }


class IssueLeaseCommandTests(unittest.TestCase):
    def test_parse_claim_renew_and_release(self):
        self.assertEqual(
            parse_lease_comment(f"/jet-agent claim chatgpt {CLAIM_A} 90"),
            {"operation": "claim", "owner": "chatgpt", "claim_id": CLAIM_A,
             "duration_minutes": 90},
        )
        self.assertEqual(
            parse_lease_comment(f"/jet-agent renew grok {CLAIM_A} {CLAIM_B}"),
            {"operation": "renew", "owner": "grok", "previous_claim_id": CLAIM_A,
             "claim_id": CLAIM_B, "duration_minutes": 60},
        )
        self.assertEqual(
            parse_lease_comment(f"/jet-agent release chatgpt {CLAIM_A}"),
            {"operation": "release", "owner": "chatgpt", "claim_id": CLAIM_A},
        )

    def test_rejects_unknown_malformed_or_multiline_commands(self):
        for body in (
            f"/jet-agent claim chatgpt {CLAIM_A}\nrun arbitrary",
            f"/jet-agent claim chatgpt ../../unsafe",
            f"/jet-agent claim admin {CLAIM_A}",
            f"/jet-agent renew chatgpt {CLAIM_A} {CLAIM_A}",
            f"/jet-agent claim chatgpt {CLAIM_A} 999",
            f"/jet-agent execute chatgpt {CLAIM_A}",
        ):
            with self.subTest(body=body), self.assertRaises(IssueLeaseCommandError):
                parse_lease_comment(body)

    def test_builds_request_only_for_open_labeled_issue_and_trusted_author(self):
        request = build_issue_lease_request(issue_event(f"/jet-agent claim chatgpt {CLAIM_A}"))
        self.assertEqual(request["task_id"], "sample-task")
        self.assertEqual(request["repository"], JET_REPOSITORY)
        with self.assertRaises(IssueLeaseCommandError):
            build_issue_lease_request(issue_event(f"/jet-agent claim chatgpt {CLAIM_A}",
                                                  association="NONE"))
        closed = issue_event(f"/jet-agent claim chatgpt {CLAIM_A}")
        closed["issue"]["state"] = "closed"
        with self.assertRaises(IssueLeaseCommandError):
            build_issue_lease_request(closed)
        unlabeled = issue_event(f"/jet-agent claim chatgpt {CLAIM_A}")
        unlabeled["issue"]["labels"] = []
        with self.assertRaises(IssueLeaseCommandError):
            build_issue_lease_request(unlabeled)

    def test_enforces_task_agent_assignment(self):
        event = issue_event(f"/jet-agent claim grok {CLAIM_A}", assigned_agent="chatgpt")
        with self.assertRaisesRegex(IssueLeaseCommandError, "assigned"):
            build_issue_lease_request(event)

    def test_claim_uses_current_main_sha_and_returns_verified_result(self):
        request = build_issue_lease_request(issue_event(f"/jet-agent claim chatgpt {CLAIM_A}"))
        with patch("tools.task_orchestrator.github_issue_lease_command.claim_or_renew") as claim:
            claim.return_value = {"task_id": "sample-task", "owner": "chatgpt",
                                  "claim_id": CLAIM_A, "base_sha": BASE,
                                  "lock_branch": "agent-locks/sample-task",
                                  "lock_commit": "d" * 40, "verified": True}
            result = execute_issue_lease_command(request, token="test-token", base_sha=BASE,
                                                 now="2026-11-23T10:00:00Z")
        self.assertEqual(result["result"]["base_sha"], BASE)
        self.assertEqual(claim.call_args.kwargs["base_sha"], BASE)

    def test_renew_uses_existing_pinned_base_and_previous_claim(self):
        request = build_issue_lease_request(
            issue_event(f"/jet-agent renew chatgpt {CLAIM_A} {CLAIM_B}")
        )
        with patch("tools.task_orchestrator.github_issue_lease_command.claim_or_renew") as claim:
            claim.return_value = {"task_id": "sample-task", "owner": "chatgpt",
                                  "claim_id": CLAIM_B, "base_sha": BASE,
                                  "lock_branch": "agent-locks/sample-task",
                                  "lock_commit": "e" * 40, "verified": True}
            execute_issue_lease_command(request, token="test-token",
                                        now="2026-11-23T10:30:00Z")
        self.assertIsNone(claim.call_args.kwargs["base_sha"])
        self.assertEqual(claim.call_args.kwargs["previous_claim_id"], CLAIM_A)

    def test_release_calls_only_the_fixed_release_operation(self):
        request = build_issue_lease_request(issue_event(f"/jet-agent release chatgpt {CLAIM_A}"))
        with patch("tools.task_orchestrator.github_issue_lease_command.release") as release:
            release.return_value = {"status": "released", "verified": True}
            result = execute_issue_lease_command(request, token="test-token",
                                                 now="2026-11-23T10:30:00Z")
        release.assert_called_once()
        self.assertEqual(result["operation"], "release")

    def test_registered_v2_project_cannot_claim_a_lease_from_read_only_intake(self):
        from pathlib import Path
        from tools.task_orchestrator.project_registry import manifest_digest
        root = Path(__file__).resolve().parents[3]
        schema = json.loads((root / "docs/PROJECT_MANIFEST_SCHEMA.json").read_text(encoding="utf-8"))
        manifest = dict(schema["examples"][0])
        manifest["lifecycle"] = "registered"
        binding = {
            "project_id": manifest["project_id"],
            "repository_id": manifest["repository"]["repository_id"],
            "repository_full_name": manifest["repository"]["full_name"],
            "default_branch": manifest["repository"]["default_branch"],
            "manifest_schema_version": manifest["schema_version"],
            "manifest_sha256": manifest_digest(manifest),
        }
        event = issue_event(f"/jet-agent claim chatgpt {CLAIM_A}")
        ticks = chr(96) * 3
        event["issue"]["body"] = chr(10).join([
            "<!-- jet-agent-task:v2 -->", "", ticks + "json",
            json.dumps({
                "schema_version": 2, "task_id": "sample-task",
                "goal": "A bounded test task.", "capability": "documentation", "risk": "low",
                "assigned_agent": "any", "allow": ["docs/**"], "exclude": [],
                "scope_reason": "Documentation-only validation.",
                "verification_profiles": ["python-tooling-tests"], "project_binding": binding,
            }),
            ticks,
        ])
        with patch(
            "tools.task_orchestrator.github_issue_lease_command.load_project_configuration",
            return_value=(schema, [manifest]),
        ):
            with self.assertRaises(IssueLeaseCommandError):
                build_issue_lease_request(event)

    def test_v2_issue_lease_request_and_execution_preserve_project_binding(self):
        from pathlib import Path
        from tools.task_orchestrator.project_registry import manifest_digest
        root = Path(__file__).resolve().parents[3]
        schema = json.loads((root / "docs/PROJECT_MANIFEST_SCHEMA.json").read_text(encoding="utf-8"))
        manifest = dict(schema["examples"][0])
        manifest["lifecycle"] = "active"
        binding = {
            "project_id": manifest["project_id"],
            "repository_id": manifest["repository"]["repository_id"],
            "repository_full_name": manifest["repository"]["full_name"],
            "default_branch": manifest["repository"]["default_branch"],
            "manifest_schema_version": manifest["schema_version"],
            "manifest_sha256": manifest_digest(manifest),
        }
        event = issue_event(f"/jet-agent claim chatgpt {CLAIM_A}")
        ticks = chr(96) * 3
        event["issue"]["body"] = (
            "<!-- jet-agent-task:v2 -->\n\n" + ticks + "json\n" +
            json.dumps({
                "schema_version": 2, "task_id": "sample-task",
                "goal": "A bounded test task.", "capability": "documentation", "risk": "low",
                "assigned_agent": "any", "allow": ["docs/**"], "exclude": [],
                "scope_reason": "Documentation-only validation.",
                "verification_profiles": ["python-tooling-tests"], "project_binding": binding,
            }) + "\n" + ticks
        )
        with patch(
            "tools.task_orchestrator.github_issue_lease_command.load_project_configuration",
            return_value=(schema, [manifest]),
        ):
            request = build_issue_lease_request(event)
        self.assertEqual(request["project_binding"], binding)
        with patch("tools.task_orchestrator.github_issue_lease_command.claim_or_renew") as claim:
            claim.return_value = {
                "task_id": "sample-task", "owner": "chatgpt", "claim_id": CLAIM_A,
                "base_sha": BASE, "lock_branch": "agent-locks/projects/" +
                manifest["project_id"] + "/" + str(manifest["repository"]["repository_id"]) +
                "/sample-task", "lock_commit": "d" * 40, "verified": True,
                "project_binding": binding,
            }
            execute_issue_lease_command(request, token="test-token", base_sha=BASE,
                                        now="2026-11-23T10:00:00Z")
        self.assertEqual(claim.call_args.kwargs["project_binding"], binding)


if __name__ == "__main__":
    unittest.main()
