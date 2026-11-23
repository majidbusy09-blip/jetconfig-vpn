import json
import unittest
from unittest.mock import patch

from tools.task_orchestrator.openai_planner import (
    OpenAIPlannerError,
    _task_projection,
    plan_with_openai,
)


def task_record():
    return {
        "task_id": "planner-smoke",
        "goal": "Add a safe server health indicator.",
        "capability_improved": "Implement a small UI feature",
        "risk": "low",
        "scope": {
            "allowed": ["lib/features/**"],
            "excluded": ["lib/secrets.dart"],
            "reason": "UI-only change",
        },
        "planned_checks": ["flutter-analysis", "flutter-tests"],
        "repository": {"origin": "https://example.invalid/private.git", "base_sha": "a" * 40},
        "context_package": {
            "project_context": [{"path": "AGENTS.md", "content": "PRIVATE SOURCE MUST NOT LEAVE"}],
            "source_context": [{"path": "lib/private.dart", "content": "PRIVATE SOURCE MUST NOT LEAVE"}],
        },
        "semantic_artifacts": {"raw": "PRIVATE SOURCE MUST NOT LEAVE"},
    }


def api_response(plan):
    return {
        "output": [{
            "type": "message",
            "content": [{"type": "output_text", "text": json.dumps(plan)}],
        }]
    }


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.payload


class OpenAIPlannerTests(unittest.TestCase):
    def test_projection_excludes_all_repository_and_source_content(self):
        projection = _task_projection("planner-smoke", task_record())
        serialized = json.dumps(projection)
        self.assertNotIn("PRIVATE SOURCE MUST NOT LEAVE", serialized)
        self.assertNotIn("example.invalid", serialized)
        self.assertNotIn("base_sha", serialized)
        self.assertEqual(projection["goal"], task_record()["goal"])

    def test_missing_credentials_or_model_never_calls_transport(self):
        def forbidden(*args, **kwargs):
            raise AssertionError("transport must not be called")
        with self.assertRaises(OpenAIPlannerError):
            plan_with_openai("planner-smoke", task_record(), api_key="", model="gpt-test", opener=forbidden)
        with self.assertRaises(OpenAIPlannerError):
            plan_with_openai("planner-smoke", task_record(), api_key="sk-test", model="", opener=forbidden)

    def test_request_contains_only_minimal_task_metadata_and_no_tools(self):
        plan = {
            "summary": "A small, bounded UI task.",
            "plan": ["Inspect the UI entry point.", "Propose a minimal implementation."],
            "assumptions": [],
            "questions": [],
            "risk_notes": ["No source files were supplied to the planner."],
        }
        captured = {}

        def fake_open(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data)
            captured["timeout"] = timeout
            return FakeResponse(api_response(plan))

        result = plan_with_openai(
            "planner-smoke", task_record(), api_key="sk-test", model="gpt-test", opener=fake_open
        )
        body = captured["body"]
        self.assertEqual(captured["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(captured["timeout"], 30)
        self.assertNotIn("tools", body)
        self.assertNotIn("PRIVATE SOURCE MUST NOT LEAVE", body["input"])
        self.assertNotIn("example.invalid", body["input"])
        self.assertEqual(result["source_files_sent"], 0)
        self.assertFalse(result["tools_enabled"])
        self.assertEqual(result["mode"], "planning_only")
        self.assertEqual(result["plan"]["summary"], plan["summary"])

    def test_rejects_invalid_provider_output(self):
        bad = {"summary": "ok", "plan": [], "assumptions": [], "questions": [], "risk_notes": []}
        with self.assertRaises(OpenAIPlannerError):
            plan_with_openai(
                "planner-smoke", task_record(), api_key="sk-test", model="gpt-test",
                opener=lambda *args, **kwargs: FakeResponse(api_response(bad)),
            )

    def test_provider_error_does_not_leak_response_or_key(self):
        from urllib.error import HTTPError
        def failing(*args, **kwargs):
            raise HTTPError("https://api.openai.com/v1/responses", 401, "unauthorized sk-test", {}, None)
        with self.assertRaises(OpenAIPlannerError) as raised:
            plan_with_openai(
                "planner-smoke", task_record(), api_key="sk-test", model="gpt-test", opener=failing
            )
        self.assertNotIn("sk-test", str(raised.exception))
        self.assertNotIn("unauthorized", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
