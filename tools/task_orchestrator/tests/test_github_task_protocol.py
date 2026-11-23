import json
import unittest
from tools.task_orchestrator.github_task_protocol import GitHubTaskError, validate_issue_body, validate_task_payload

PAYLOAD = {
    "schema_version": 1, "task_id": "smart-server-health",
    "goal": "Improve server health selection and report measured behavior.",
    "capability": "implementation", "risk": "medium", "assigned_agent": "any",
    "allow": ["lib/**", "test/**"], "exclude": ["lib/secrets.dart"],
    "scope_reason": "Keep the task within application logic and tests.",
    "verification_profiles": ["flutter-analysis", "flutter-tests"],
}


def issue_body(payload=PAYLOAD):
    fence = chr(96) * 3
    return "<!-- jet-agent-task:v1 -->\n\n" + fence + "json\n" + json.dumps(payload) + "\n" + fence + "\n"


class GitHubTaskProtocolTests(unittest.TestCase):
    def test_accepts_valid_shared_task(self):
        result = validate_issue_body(issue_body())
        self.assertEqual(result["task_id"], "smart-server-health")
        self.assertEqual(result["assigned_agent"], "any")

    def test_rejects_duplicate_json_keys(self):
        raw = '{"schema_version":1,"schema_version":1}'
        fence = chr(96) * 3
        with self.assertRaises(GitHubTaskError):
            validate_issue_body("<!-- jet-agent-task:v1 -->\n" + fence + "json\n" + raw + "\n" + fence)

    def test_requires_exactly_one_marker_and_payload(self):
        with self.assertRaises(GitHubTaskError):
            validate_issue_body("no structured task here")
        with self.assertRaises(GitHubTaskError):
            validate_issue_body(issue_body() + issue_body())

    def test_rejects_path_traversal_and_protected_paths(self):
        for path in ("../lib/main.dart", "/etc/passwd", "lib/../secrets", ".agent/tasks/**", ".github/workflows/**"):
            with self.subTest(path=path), self.assertRaises(GitHubTaskError):
                validate_task_payload(dict(PAYLOAD, allow=[path]))

    def test_rejects_unknown_agent_capability_and_profile(self):
        for key, value in (("assigned_agent", "unknown-agent"), ("capability", "deploy"), ("verification_profiles", ["arbitrary-shell"])):
            with self.subTest(key=key), self.assertRaises(GitHubTaskError):
                validate_task_payload(dict(PAYLOAD, **{key: value}))

    def test_rejects_unknown_fields_and_oversized_goal(self):
        with self.assertRaises(GitHubTaskError):
            validate_task_payload(dict(PAYLOAD, shell="rm -rf"))
        with self.assertRaises(GitHubTaskError):
            validate_task_payload(dict(PAYLOAD, goal="x" * 8001))


if __name__ == "__main__":
    unittest.main()
