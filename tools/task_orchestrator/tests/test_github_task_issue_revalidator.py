import unittest
from unittest.mock import patch

from tools.task_orchestrator.github_task_issue_revalidator import (
    RevalidationError, revalidate_issue_event,
)

REPOSITORY = "owner/repository"


def task_body():
    import json
    task = {
        "schema_version": 1, "task_id": "task-42",
        "goal": "Bounded docs update.", "capability": "documentation",
        "risk": "low", "assigned_agent": "any",
        "allow": ["docs/**"], "exclude": ["docs/private/**"],
        "scope_reason": "Docs only.",
        "verification_profiles": ["python-tooling-tests"],
    }
    fence = chr(96) * 3
    return "<!-- jet-agent-task:v1 -->\n" + fence + "json\n" + json.dumps(task) + "\n" + fence


def issue_event(action="edited"):
    return {
        "action": action,
        "repository": {"full_name": REPOSITORY},
        "issue": {
            "number": 42, "state": "open", "body": task_body(),
            "labels": [{"name": "agent-task"}],
        },
    }


class TaskIssueRevalidatorTests(unittest.TestCase):
    def test_non_task_issue_is_skipped_without_api_scan(self):
        event = issue_event()
        event["issue"]["labels"] = []
        with patch("tools.task_orchestrator.github_task_issue_revalidator.api_get") as api:
            result = revalidate_issue_event(event, token="read-token", repository=REPOSITORY)
        self.assertEqual(result["status"], "not-agent-task")
        api.assert_not_called()

    def test_unlabeling_agent_task_still_revalidates_linked_prs(self):
        event = issue_event("unlabeled")
        event["issue"]["labels"] = []
        event["label"] = {"name": "agent-task"}
        with patch(
            "tools.task_orchestrator.github_task_issue_revalidator.api_get",
            return_value=[],
        ) as api:
            result = revalidate_issue_event(event, token="read-token", repository=REPOSITORY)
        self.assertEqual(result["status"], "revalidated")
        self.assertEqual(result["checked_prs"], 0)
        api.assert_called_once()

    def test_issue_event_revalidates_only_prs_linked_by_envelope(self):
        from tools.task_orchestrator.github_task_pr_guard import MARKER
        import json
        fence = chr(96) * 3
        body = MARKER + "\n" + fence + "json\n" + json.dumps({
            "schema_version": 1, "task_issue": 42,
            "owner": "chatgpt", "claim_id": "a" * 16,
        }) + "\n" + fence
        pr = {
            "number": 9, "state": "open", "body": body,
            "base": {"ref": "main", "sha": "b" * 40,
                     "repo": {"full_name": REPOSITORY}},
            "head": {"sha": "c" * 40, "ref": "agent/task-42",
                     "repo": {"full_name": REPOSITORY}},
        }
        with patch(
            "tools.task_orchestrator.github_task_issue_revalidator.api_get",
            return_value=[pr],
        ), patch(
            "tools.task_orchestrator.github_task_issue_revalidator.validate_agent_pr",
            return_value={"status": "validated-agent-pr", "pr_number": 9},
        ) as validate:
            result = revalidate_issue_event(issue_event(), token="read-token",
                                            repository=REPOSITORY)
        self.assertEqual(result["checked_prs"], 1)
        validate.assert_called_once()

    def test_rejects_invalid_event_and_invalid_task_body(self):
        with self.assertRaises(RevalidationError):
            revalidate_issue_event(issue_event("deleted"), token="x", repository=REPOSITORY)
        event = issue_event()
        event["issue"]["body"] = "invalid"
        with patch("tools.task_orchestrator.github_task_issue_revalidator.api_get") as api:
            with self.assertRaises(RevalidationError):
                revalidate_issue_event(event, token="x", repository=REPOSITORY)
        api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
