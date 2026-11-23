import unittest
from tools.task_orchestrator.github_issue_intake import IntakeError, build_intake

PAYLOAD = {
    "schema_version": 1, "task_id": "sample-task",
    "goal": "Improve a bounded feature and verify it.",
    "capability": "implementation", "risk": "low", "assigned_agent": "any",
    "allow": ["lib/**"], "exclude": ["lib/secrets.dart"],
    "scope_reason": "Keep the change within application code.",
    "verification_profiles": ["flutter-analysis"],
}
def event(**issue_overrides):
    fence = chr(96) * 3
    body = "<!-- jet-agent-task:v1 -->\n" + fence + "json\n" + __import__("json").dumps(PAYLOAD) + "\n" + fence
    issue = {"number": 42, "title": "Sample task", "body": body, "state": "open",
             "html_url": "https://github.com/acme/project/issues/42",
             "labels": [{"name": "agent-task"}]}
    issue.update(issue_overrides)
    return {"action": "opened", "repository": {"full_name": "acme/project"}, "issue": issue}

class GitHubIssueIntakeTests(unittest.TestCase):
    def test_builds_validated_non_executing_artifact(self):
        result = build_intake(event())
        self.assertEqual(result["task"]["task_id"], "sample-task")
        self.assertEqual(result["execution"]["status"], "validated-awaiting-claim")
        self.assertFalse(result["execution"]["agent_dispatched"])
        self.assertFalse(result["execution"]["lease_claimed"])

    def test_rejects_missing_label_closed_issue_and_pull_request(self):
        for issue in ({"labels": []}, {"state": "closed"},
                      {"pull_request": {"url": "https://api.github.com/pulls/42"}}):
            with self.subTest(issue=issue), self.assertRaises(IntakeError):
                build_intake(event(**issue))

    def test_rejects_untrusted_or_ineligible_event(self):
        edited = build_intake(dict(event(), action="edited"))
        self.assertEqual(edited["task"]["task_id"], "sample-task")
        with self.assertRaises(IntakeError):
            build_intake({"action": "opened", "issue": {}, "repository": {}})

    def test_rejects_invalid_task_payload(self):
        bad = event(body="plain text")
        with self.assertRaises(IntakeError):
            build_intake(bad)

if __name__ == "__main__":
    unittest.main()
