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
        "repository": {"full_name": "owner/repository"},
        "issue": {
            "number": 42,
            "state": "open",
            "title": "[JET-AGENT] Sample task",
            "body": body,
            "html_url": "https://github.com/owner/repository/issues/42",
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
        self.assertEqual(request["repository"], "owner/repository")
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


if __name__ == "__main__":
    unittest.main()
