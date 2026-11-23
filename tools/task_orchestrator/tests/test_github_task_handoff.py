import unittest

from tools.task_orchestrator.github_task_handoff import (
    TaskHandoffError, build_task_handoff,
)

CLAIM = "a" * 16
BASE = "b" * 40
LOCK = "c" * 40
EXPIRES = "2030-01-01T01:00:00Z"


def event(operation="claim"):
    import json
    task = {
        "schema_version": 1,
        "task_id": "sample-task",
        "goal": "A bounded task for the handoff test.",
        "capability": "documentation",
        "risk": "low",
        "assigned_agent": "any",
        "allow": ["docs/**"],
        "exclude": [],
        "scope_reason": "Documentation-only.",
        "verification_profiles": ["python-tooling-tests"],
    }
    body = "<!-- jet-agent-task:v1 -->\n\n" + "```json\n" + json.dumps(task) + "\n```"
    command = f"/jet-agent {operation} chatgpt {CLAIM}"
    if operation == "renew":
        command = f"/jet-agent renew chatgpt {'d' * 16} {CLAIM}"
    return {
        "action": "created",
        "repository": {"full_name": "owner/repository"},
        "issue": {
            "number": 42,
            "state": "open",
            "title": "[JET-AGENT] Handoff test",
            "body": body,
            "html_url": "https://github.com/owner/repository/issues/42",
            "labels": [{"name": "agent-task"}],
        },
        "comment": {"body": command, "author_association": "OWNER"},
    }


def lease_result(operation="claim"):
    return {
        "operation": operation,
        "task_id": "sample-task",
        "issue_number": 42,
        "issue_url": "https://github.com/owner/repository/issues/42",
        "result": {
            "task_id": "sample-task",
            "owner": "chatgpt",
            "claim_id": CLAIM,
            "status": "active",
            "base_sha": BASE,
            "expires_at": EXPIRES,
            "lock_branch": "agent-locks/sample-task",
            "lock_commit": LOCK,
            "verified": True,
        },
    }


class TaskHandoffTests(unittest.TestCase):
    def test_builds_handoff_bound_to_verified_active_lease(self):
        result = build_task_handoff(
            event(), lease_result(), run_id=12345, run_attempt=2,
            now="2029-12-31T23:00:00Z",
        )
        self.assertEqual(result["handoff_schema"], 1)
        self.assertEqual(result["issue"]["number"], 42)
        self.assertEqual(result["lease"]["base_sha"], BASE)
        self.assertEqual(result["lease"]["lock_commit"], LOCK)
        self.assertEqual(result["execution"]["status"], "ready-for-agent")
        self.assertFalse(result["execution"]["agent_dispatched"])
        self.assertFalse(result["execution"]["model_called"])
        self.assertFalse(result["execution"]["source_uploaded"])
        self.assertFalse(result["execution"]["patch_applied"])
        self.assertEqual(result["workflow"], {"run_id": 12345, "run_attempt": 2})

    def test_supports_renewal_but_not_release(self):
        result = build_task_handoff(
            event("renew"), lease_result("renew"), run_id=1, run_attempt=1,
            now="2029-12-31T23:00:00Z",
        )
        self.assertEqual(result["lease"]["claim_id"], CLAIM)
        with self.assertRaises(TaskHandoffError):
            build_task_handoff(
                event("release"), lease_result("release"), run_id=1, run_attempt=1,
                now="2029-12-31T23:00:00Z",
            )

    def test_rejects_mismatched_or_unverified_lease(self):
        for mutate in (
            lambda p: p.update(task_id="other-task"),
            lambda p: p.update(issue_number=99),
            lambda p: p["result"].update(claim_id="d" * 16),
            lambda p: p["result"].update(verified=False),
            lambda p: p["result"].update(status="released"),
            lambda p: p["result"].update(lock_branch="agent-locks/other-task"),
            lambda p: p["result"].update(lock_commit="not-a-sha"),
        ):
            payload = lease_result()
            mutate(payload)
            with self.subTest(payload=payload), self.assertRaises(TaskHandoffError):
                build_task_handoff(
                    event(), payload, run_id=1, run_attempt=1,
                    now="2029-12-31T23:00:00Z",
                )

    def test_rejects_expired_lease_and_invalid_run_identity(self):
        payload = lease_result()
        payload["result"]["expires_at"] = "2029-12-31T22:59:59Z"
        with self.assertRaisesRegex(TaskHandoffError, "expired"):
            build_task_handoff(
                event(), payload, run_id=1, run_attempt=1,
                now="2029-12-31T23:00:00Z",
            )
        with self.assertRaises(TaskHandoffError):
            build_task_handoff(
                event(), lease_result(), run_id=0, run_attempt=1,
                now="2029-12-31T23:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
