import hashlib
import unittest

from tools.task_orchestrator.github_lease import make_lease
from tools.task_orchestrator.github_task_handoff import build_task_handoff
from tools.task_orchestrator.github_task_handoff_accept import (
    HandoffAcceptanceError, validate_handoff_for_acceptance,
)

REPOSITORY = "owner/repository"
TASK_ID = "sample-task"
CLAIM = "a" * 16
BASE = "b" * 40
LOCK_COMMIT = "c" * 40
NOW = "2029-12-31T23:00:00Z"
EXPIRES = "2030-01-01T01:00:00Z"


def issue_event():
    import json
    task = {
        "schema_version": 1, "task_id": TASK_ID,
        "goal": "A bounded task for the handoff acceptance test.",
        "capability": "documentation", "risk": "low",
        "assigned_agent": "any", "allow": ["docs/**"], "exclude": [],
        "scope_reason": "Documentation-only.", "verification_profiles": ["python-tooling-tests"],
    }
    body = "<!-- jet-agent-task:v1 -->\n\n" + "```json\n" + json.dumps(task) + "\n```"
    return {
        "action": "created",
        "repository": {"full_name": REPOSITORY},
        "issue": {
            "number": 42, "state": "open", "body": body,
            "html_url": "https://github.com/owner/repository/issues/42",
            "labels": [{"name": "agent-task"}],
        },
        "comment": {"body": f"/jet-agent claim chatgpt {CLAIM}", "author_association": "OWNER"},
    }


def manifest():
    event = issue_event()
    import json
    task = json.loads(event["issue"]["body"].split("```json\n", 1)[1].split("\n```", 1)[0])
    result = {
        "operation": "claim", "task_id": TASK_ID, "issue_number": 42,
        "issue_url": event["issue"]["html_url"],
        "result": {
            "task_id": TASK_ID, "owner": "chatgpt", "claim_id": CLAIM,
            "status": "active", "base_sha": BASE, "expires_at": EXPIRES,
            "lock_branch": "agent-locks/" + TASK_ID,
            "lock_commit": LOCK_COMMIT, "verified": True,
        },
    }
    return build_task_handoff(event, result, run_id=123, run_attempt=1, now=NOW)


def current_issue():
    event = issue_event()
    return {
        "number": 42, "state": "open", "body": event["issue"]["body"],
        "html_url": event["issue"]["html_url"],
        "labels": [{"name": "agent-task"}],
    }


def current_lease():
    return make_lease(
        task_id=TASK_ID, owner="chatgpt", claim_id=CLAIM,
        base_sha=BASE, now="2029-12-31T23:00:00Z", duration_minutes=120,
    )


class HandoffAcceptanceTests(unittest.TestCase):
    def test_accepts_current_issue_and_exact_active_remote_lease(self):
        accepted = validate_handoff_for_acceptance(
            manifest(), current_issue(), current_lease(), LOCK_COMMIT,
            repository=REPOSITORY, now=NOW,
        )
        self.assertEqual(accepted["task_id"], TASK_ID)
        self.assertEqual(accepted["assigned_agent"], "any")

    def test_rejects_changed_or_closed_issue(self):
        for mutate in (
            lambda issue: issue.update(state="closed"),
            lambda issue: issue.update(body=issue["body"] + "\nchanged"),
            lambda issue: issue.update(labels=[]),
            lambda issue: issue.update(number=99),
            lambda issue: issue.update(html_url="https://github.com/owner/repository/issues/99"),
        ):
            issue = current_issue()
            mutate(issue)
            with self.subTest(issue=issue), self.assertRaises(HandoffAcceptanceError):
                validate_handoff_for_acceptance(
                    manifest(), issue, current_lease(), LOCK_COMMIT,
                    repository=REPOSITORY, now=NOW,
                )

    def test_rejects_mismatched_task_lease_and_lock_ref(self):
        for lease_mutation, lock_sha in (
            ({"claim_id": "d" * 16}, LOCK_COMMIT),
            ({"owner": "grok"}, LOCK_COMMIT),
            ({"base_sha": "e" * 40}, LOCK_COMMIT),
            ({"status": "released"}, LOCK_COMMIT),
            ({}, "f" * 40),
        ):
            lease = current_lease()
            lease.update(lease_mutation)
            with self.subTest(lease=lease, lock_sha=lock_sha), self.assertRaises(HandoffAcceptanceError):
                validate_handoff_for_acceptance(
                    manifest(), current_issue(), lease, lock_sha,
                    repository=REPOSITORY, now=NOW,
                )

    def test_rejects_modified_manifest_and_wrong_repository(self):
        payload = manifest()
        payload["task"]["goal"] = "Tampered goal"
        with self.assertRaises(HandoffAcceptanceError):
            validate_handoff_for_acceptance(
                payload, current_issue(), current_lease(), LOCK_COMMIT,
                repository=REPOSITORY, now=NOW,
            )
        with self.assertRaises(HandoffAcceptanceError):
            validate_handoff_for_acceptance(
                manifest(), current_issue(), current_lease(), LOCK_COMMIT,
                repository="other/repository", now=NOW,
            )

    def test_rejects_expired_lease_and_execution_flags(self):
        lease = current_lease()
        lease["expires_at"] = "2029-12-31T22:59:59Z"
        with self.assertRaises(HandoffAcceptanceError):
            validate_handoff_for_acceptance(
                manifest(), current_issue(), lease, LOCK_COMMIT,
                repository=REPOSITORY, now=NOW,
            )
        payload = manifest()
        payload["execution"]["model_called"] = True
        with self.assertRaises(HandoffAcceptanceError):
            validate_handoff_for_acceptance(
                payload, current_issue(), current_lease(), LOCK_COMMIT,
                repository=REPOSITORY, now=NOW,
            )


if __name__ == "__main__":
    unittest.main()
