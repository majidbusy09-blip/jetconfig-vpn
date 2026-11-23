import base64
import json
import unittest
from unittest.mock import patch

from tools.task_orchestrator.github_lease import make_lease
from tools.task_orchestrator.github_task_pr_guard import (
    GuardError, parse_pr_envelope, validate_paths, validate_agent_pr,
)

REPOSITORY = "owner/repository"
BASE = "a" * 40
HEAD = "b" * 40
LOCK = "c" * 40
CLAIM = "d" * 16


def task_body(assigned="any"):
    task = {
        "schema_version": 1,
        "task_id": "sample-task",
        "goal": "A bounded documentation task.",
        "capability": "documentation",
        "risk": "low",
        "assigned_agent": assigned,
        "allow": ["docs/**"],
        "exclude": ["docs/private/**"],
        "scope_reason": "Documentation only.",
        "verification_profiles": ["python-tooling-tests"],
    }
    ticks = chr(96) * 3
    return "<!-- jet-agent-task:v1 -->\n\n" + ticks + "json\n" + json.dumps(task) + "\n" + ticks


def pr_body():
    envelope = {"schema_version": 1, "task_issue": 42, "owner": "chatgpt", "claim_id": CLAIM}
    ticks = chr(96) * 3
    return "Agent work summary.\n\n<!-- jet-agent-pr:v1 -->\n\n" + ticks + "json\n" + json.dumps(envelope) + "\n" + ticks


def event():
    return {
        "repository": {"full_name": REPOSITORY},
        "pull_request": {
            "number": 7,
            "body": pr_body(),
            "base": {"ref": "main", "sha": "e" * 40, "repo": {"full_name": REPOSITORY}},
            "head": {"sha": HEAD, "ref": "agent/sample-task", "repo": {"full_name": REPOSITORY}},
        },
    }


def api_responses(*, lease_status="active", expires="2026-11-23T11:00:00Z",
                  assigned="any", merge_base=BASE, files=None):
    lease = make_lease(task_id="sample-task", owner="chatgpt", claim_id=CLAIM,
                       base_sha=BASE, now="2026-11-23T10:00:00Z", duration_minutes=60)
    lease["status"] = lease_status
    lease["expires_at"] = expires
    encoded = base64.b64encode((json.dumps(lease) + "\n").encode()).decode()
    def api(repository, path, token):
        if path == "/issues/42":
            return {"state": "open", "labels": [{"name": "agent-task"}],
                    "body": task_body(assigned)}
        if path == "/git/ref/heads/agent-locks/sample-task":
            return {"object": {"sha": LOCK}}
        if path.startswith("/contents/.agent-locks/lease.json?"):
            return {"encoding": "base64", "content": encoded}
        if path.startswith("/compare/"):
            return {"merge_base_commit": {"sha": merge_base}}
        if path.startswith("/pulls/7/files?"):
            return files if files is not None else [{"filename": "docs/guide.md", "status": "modified"}]
        raise AssertionError("Unexpected API path: " + path)
    return api


class TaskPRGuardTests(unittest.TestCase):
    def test_parse_envelope_and_skip_non_agent_pr(self):
        parsed = parse_pr_envelope(pr_body())
        self.assertEqual(parsed["task_issue"], 42)
        self.assertEqual(parse_pr_envelope("ordinary PR body"), None)

    def test_rejects_duplicate_or_extra_envelope_fields(self):
        ticks = chr(96) * 3
        duplicate = "<!-- jet-agent-pr:v1 -->\n" + ticks + 'json\n{"schema_version":1,"task_issue":42,"owner":"chatgpt","claim_id":"' + CLAIM + '","claim_id":"' + CLAIM + '"}\n' + ticks
        with self.assertRaises(GuardError):
            parse_pr_envelope(duplicate)
        extra = {"schema_version": 1, "task_issue": 42, "owner": "chatgpt",
                 "claim_id": CLAIM, "arbitrary": True}
        invalid = "<!-- jet-agent-pr:v1 -->\n" + ticks + "json\n" + json.dumps(extra) + "\n" + ticks
        with self.assertRaises(GuardError):
            parse_pr_envelope(invalid)

    def test_changed_paths_enforce_allow_exclude_and_protected_paths(self):
        self.assertEqual(validate_paths([{"filename": "docs/guide.md"}], ["docs/**"], []),
                         ["docs/guide.md"])
        for filename, allow, exclude in (
            ("lib/main.dart", ["docs/**"], []),
            ("docs/private/secret.md", ["docs/**"], ["docs/private/**"]),
            (".github/workflows/deploy.yml", ["**"], []),
            ("../escape.md", ["**"], []),
        ):
            with self.subTest(filename=filename), self.assertRaises(GuardError):
                validate_paths([{"filename": filename}], allow, exclude)

    def test_live_metadata_validation_accepts_matching_active_lease_and_scope(self):
        with patch("tools.task_orchestrator.github_task_pr_guard.api_get",
                   side_effect=api_responses()):
            result = validate_agent_pr(event(), token="read-token", repository=REPOSITORY,
                                       now="2026-11-23T10:30:00Z")
        self.assertEqual(result["status"], "validated-agent-pr")
        self.assertEqual(result["task_id"], "sample-task")
        self.assertEqual(result["changed_paths"], ["docs/guide.md"])
        self.assertEqual(result["base_sha"], BASE)

    def test_rejects_expired_or_released_lease(self):
        for options in (
            {"lease_status": "released"},
            {"expires": "2026-11-23T10:20:00Z"},
        ):
            with self.subTest(options=options), patch(
                "tools.task_orchestrator.github_task_pr_guard.api_get",
                side_effect=api_responses(**options),
            ), self.assertRaises(GuardError):
                validate_agent_pr(event(), token="read-token", repository=REPOSITORY,
                                  now="2026-11-23T10:30:00Z")

    def test_rejects_base_mismatch_assignment_and_out_of_scope_files(self):
        cases = (
            api_responses(merge_base="f" * 40),
            api_responses(assigned="grok"),
            api_responses(files=[{"filename": "lib/main.dart", "status": "modified"}]),
        )
        for api in cases:
            with patch("tools.task_orchestrator.github_task_pr_guard.api_get", side_effect=api), \
                 self.assertRaises(GuardError):
                validate_agent_pr(event(), token="read-token", repository=REPOSITORY,
                                  now="2026-11-23T10:30:00Z")

    def test_requires_main_target_and_same_repository_head(self):
        bad_base = event()
        bad_base["pull_request"]["base"]["ref"] = "release"
        bad_head = event()
        bad_head["pull_request"]["head"]["repo"]["full_name"] = "fork/repository"
        for item in (bad_base, bad_head):
            with self.subTest(item=item), self.assertRaises(GuardError):
                validate_agent_pr(item, token="read-token", repository=REPOSITORY)


if __name__ == "__main__":
    unittest.main()
