import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.task_orchestrator.github_task_handoff import (
    TaskHandoffError, build_task_handoff,
)
from tools.task_orchestrator.project_registry import manifest_digest

CLAIM = "a" * 16
BASE = "b" * 40
LOCK = "c" * 40
ROOT = Path(__file__).resolve().parents[3]
PROJECT_SCHEMA = json.loads((ROOT / "docs/PROJECT_MANIFEST_SCHEMA.json").read_text(encoding="utf-8"))
ACTIVE_MANIFEST = copy.deepcopy(PROJECT_SCHEMA["examples"][0])
ACTIVE_MANIFEST["lifecycle"] = "active"
EXPIRES = "2030-01-01T01:00:00Z"
JET_REPOSITORY = "majidbusy09-blip/jetconfig-vpn"
JET_METADATA = {"id": 1349356614, "full_name": JET_REPOSITORY, "html_url": "https://github.com/" + JET_REPOSITORY, "default_branch": "main"}


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
        "repository": dict(JET_METADATA),
        "issue": {
            "number": 42,
            "state": "open",
            "title": "[JET-AGENT] Handoff test",
            "body": body,
            "html_url": "https://github.com/majidbusy09-blip/jetconfig-vpn/issues/42",
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


def v2_event(operation="claim", previous_claim=None):
    import json
    task = {
        "schema_version": 2,
        "task_id": "sample-task",
        "goal": "A bounded task for the handoff test.",
        "capability": "documentation",
        "risk": "low",
        "assigned_agent": "any",
        "allow": ["docs/**"],
        "exclude": [],
        "scope_reason": "Documentation-only.",
        "verification_profiles": ["python-tooling-tests"],
        "project_binding": {
            "project_id": ACTIVE_MANIFEST["project_id"],
            "repository_id": ACTIVE_MANIFEST["repository"]["repository_id"],
            "repository_full_name": ACTIVE_MANIFEST["repository"]["full_name"],
            "default_branch": ACTIVE_MANIFEST["repository"]["default_branch"],
            "manifest_schema_version": ACTIVE_MANIFEST["schema_version"],
            "manifest_sha256": manifest_digest(ACTIVE_MANIFEST),
        },
    }
    body = "<!-- jet-agent-task:v2 -->\\n\\n" + "```json\\n" + json.dumps(task) + "\\n```"
    command = f"/jet-agent {operation} chatgpt {CLAIM}"
    if operation == "renew":
        command = f"/jet-agent renew chatgpt {previous_claim or ('d' * 16)} {CLAIM}"
    ev = event(operation)
    ev["issue"]["body"] = body
    return ev


def v2_project_config():
    return PROJECT_SCHEMA, [ACTIVE_MANIFEST]


class TaskHandoffTests(unittest.TestCase):
    def test_builds_handoff_bound_to_verified_active_lease(self):
        result = build_task_handoff(
            event(), lease_result(), run_id=12345, run_attempt=2,
            now="2029-12-31T23:00:00Z",
        )
        self.assertEqual(result["handoff_schema"], 2)
        self.assertEqual(result["issue"]["number"], 42)
        self.assertEqual(result["lease"]["base_sha"], BASE)
        self.assertEqual(result["lease"]["operation"], "claim")
        self.assertIsNone(result["lease"]["previous_claim_id"])
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
        self.assertEqual(result["lease"]["operation"], "renew")
        self.assertEqual(result["lease"]["previous_claim_id"], "d" * 16)
        with self.assertRaises(TaskHandoffError):
            build_task_handoff(
                event("release"), lease_result("release"), run_id=1, run_attempt=1,
                now="2029-12-31T23:00:00Z",
            )

    def test_builds_v2_handoff_with_manifest_bound_project_identity(self):
        with patch(
            "tools.task_orchestrator.github_issue_lease_command.load_project_configuration",
            return_value=v2_project_config(),
        ), patch(
            "tools.task_orchestrator.github_task_handoff.load_project_configuration",
            return_value=v2_project_config(),
        ):
            result = build_task_handoff(
                v2_event(), lease_result(), run_id=12345, run_attempt=1,
                now="2029-12-31T23:00:00Z",
            )
        self.assertEqual(result["handoff_schema"], 3)
        self.assertEqual(result["project_binding"]["project_id"], ACTIVE_MANIFEST["project_id"])
        self.assertEqual(result["project_binding"]["manifest_sha256"], manifest_digest(ACTIVE_MANIFEST))
        self.assertEqual(result["lease"]["base_sha"], BASE)


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
