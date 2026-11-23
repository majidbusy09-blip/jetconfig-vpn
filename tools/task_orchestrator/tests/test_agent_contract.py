import copy
import hashlib
import json
import unittest

from tools.task_orchestrator.agent_contract import (
    ContractValidationError,
    parse_json_object,
    validate_envelope,
    validate_result,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
PROJECT_TEXT = "# Agent rules\nFollow the repository safety contract.\n"
SOURCE_TEXT = "class RoutingPolicy {}\n"
PROJECT_SHA = "371ffdfd69786710a8682d1b89ef26c7c399919e639c99ed06a6f8111544839f"
SOURCE_SHA = "3cec9734081d2119601b9ff0188955417f781444edcfb673f2c0a66b25427192"


def envelope():
    return {
        "contract_version": "1.1",
        "task_id": "smart-routing-fix",
        "goal": "Fix the scoped Smart Routing regression safely.",
        "capability": "bug_fix",
        "risk": "medium",
        "repository": {
            "name": "majidbusy09-blip/jetconfig-vpn",
            "branch": "agent/task-smart-routing",
            "base_sha": SHA_A,
            "workspace_id": "workspace_123456",
        },
        "scope": {
            "allowed_paths": ["lib/**", "test/**"],
            "excluded_paths": ["lib/generated/**"],
            "scope_reason": "",
        },
        "project_context": [{"path": "AGENTS.md", "sha256": PROJECT_SHA, "content": PROJECT_TEXT}],
        "source_context": [{"path": "lib/routing_policy.dart", "sha256": SOURCE_SHA, "content": SOURCE_TEXT}],
        "semantic_context": {
            "status": "current",
            "source_sha": SHA_A,
            "summary": "Resolved call graph available.",
            "limitations": ["Static reachability is not runtime proof."],
        },
        "constraints": {
            "invariants": ["Do not change payment behavior."],
            "prohibited_paths": ["android/**"],
            "compatibility": ["Preserve current app version."],
            "known_risks": ["Native VPN behavior requires device testing."],
        },
        "budgets": {
            "max_wall_seconds": 900,
            "max_tokens": 30000,
            "max_tool_calls": 100,
            "max_changed_files": 10,
            "max_patch_bytes": 200000,
        },
        "verification_profiles": ["python-tooling-tests", "flutter-tests", "flutter-analysis"],
    }


def result_for(env=None):
    env = env or envelope()
    return {
        "contract_version": "1.1",
        "task_id": env["task_id"],
        "provider": "fixture-provider",
        "model": "fixture-model",
        "status": "completed",
        "summary": "Fix the routing regression and add a focused test.",
        "plan": ["Inspect routing decision", "Apply minimal fix", "Add regression test"],
        "assumptions": [{"text": "The regression is in app-owned routing logic.", "confidence": "inferred"}],
        "changed_paths": ["lib/routing_policy.dart", "test/routing_policy_test.dart"],
        "patch_ref": "artifact:sha256:" + "d" * 64,
        "tests_added_or_changed": [
            {"path": "test/routing_policy_test.dart", "purpose": "Cover the reported regression."}
        ],
        "verification_requests": [
            {"profile": "flutter-tests", "rationale": "Run the app regression suite."}
        ],
        "risks": ["Device-level VPN routing still needs physical validation."],
        "handoff_notes": "Review the patch and verify on a device.",
        "usage": {"wall_seconds": 60, "tokens": 1200, "tool_calls": 8, "patch_bytes": 4096},
        "context_fingerprints": [
            {"path": item["path"], "sha256": item["sha256"]}
            for item in env["project_context"] + env["source_context"]
        ],
    }


class AgentContractTests(unittest.TestCase):
    def test_valid_envelope_and_result(self):
        env = envelope()
        self.assertIs(validate_envelope(env), env)
        self.assertEqual(validate_result(result_for(env), env)["status"], "completed")

    def test_reject_non_object_and_missing_or_extra_fields(self):
        with self.assertRaises(ContractValidationError):
            validate_envelope([])
        bad = envelope()
        del bad["goal"]
        with self.assertRaises(ContractValidationError):
            validate_envelope(bad)
        bad = envelope()
        bad["untrusted_extra"] = "ignored?"
        with self.assertRaises(ContractValidationError):
            validate_envelope(bad)

    def test_reject_wrong_types_and_invalid_enums(self):
        for field, value in (("goal", []), ("risk", "critical"), ("capability", "shell")):
            bad = envelope()
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ContractValidationError):
                validate_envelope(bad)

    def test_reject_non_string_enum_values_without_leaking_type_errors(self):
        for field, value in (
            ("capability", []), ("capability", {}),
            ("risk", []), ("risk", {}),
        ):
            bad = envelope()
            bad[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ContractValidationError):
                validate_envelope(bad)

        for value in ([], {}):
            bad = envelope()
            bad["semantic_context"]["status"] = value
            with self.subTest(semantic_status=value), self.assertRaises(ContractValidationError):
                validate_envelope(bad)

            bad_result = result_for()
            bad_result["status"] = value
            with self.subTest(result_status=value), self.assertRaises(ContractValidationError):
                validate_result(bad_result, envelope())

            bad_result = result_for()
            bad_result["assumptions"][0]["confidence"] = value
            with self.subTest(confidence=value), self.assertRaises(ContractValidationError):
                validate_result(bad_result, envelope())

            bad_result = result_for()
            bad_result["verification_requests"][0]["profile"] = value
            with self.subTest(profile=value), self.assertRaises(ContractValidationError):
                validate_result(bad_result, envelope())

    def test_reject_invalid_task_and_contract_versions(self):
        for field, value in (("task_id", "../escape"), ("contract_version", "99")):
            bad = envelope()
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ContractValidationError):
                validate_envelope(bad)

    def test_reject_protected_default_branch_and_bad_repository(self):
        for mutate in (
            lambda x: x["repository"].update(branch="main"),
            lambda x: x["repository"].update(name="not-a-repository"),
            lambda x: x["repository"].update(base_sha="short"),
        ):
            bad = envelope()
            mutate(bad)
            with self.assertRaises(ContractValidationError):
                validate_envelope(bad)

    def test_reject_path_traversal_absolute_windows_and_dot_segments(self):
        for path in ("../secrets.txt", "/etc/passwd", "lib/../../secret", r"lib\main.dart", "lib/./x.dart"):
            bad = result_for()
            bad["changed_paths"] = [path]
            with self.subTest(path=path), self.assertRaises(ContractValidationError):
                validate_result(bad, envelope())

    def test_reject_protected_paths_and_excluded_scope(self):
        for path in (".github/workflows/build.yml", ".env", "android/app/key.properties",
                     "lib/generated/output.dart", "secrets/token.txt"):
            bad = result_for()
            bad["changed_paths"] = [path]
            with self.subTest(path=path), self.assertRaises(ContractValidationError):
                validate_result(bad, envelope())

    def test_reject_out_of_scope_and_duplicate_paths(self):
        for paths in (["README.md"], ["lib/a.dart", "lib/a.dart"]):
            bad = result_for()
            bad["changed_paths"] = paths
            with self.assertRaises(ContractValidationError):
                validate_result(bad, envelope())

    def test_scope_wildcard_does_not_cross_directory_boundary(self):
        env = envelope()
        env["scope"]["allowed_paths"] = ["lib/*.dart"]
        bad = result_for()
        bad["changed_paths"] = ["lib/nested/file.dart"]
        with self.assertRaises(ContractValidationError):
            validate_result(bad, env)

    def test_reject_glob_as_concrete_changed_path(self):
        bad = result_for()
        bad["changed_paths"] = ["lib/**"]
        with self.assertRaises(ContractValidationError):
            validate_result(bad, envelope())

    def test_reject_invalid_scope_patterns(self):
        for pattern in ("../**", "/tmp/**", r"lib\**"):
            bad = envelope()
            bad["scope"]["allowed_paths"] = [pattern]
            with self.assertRaises(ContractValidationError):
                validate_envelope(bad)

    def test_reject_invalid_or_excessive_budgets(self):
        for value in (True, 0, -1, 9000000, 1.5):
            bad = envelope()
            bad["budgets"]["max_tokens"] = value
            with self.subTest(value=value), self.assertRaises(ContractValidationError):
                validate_envelope(bad)

    def test_reject_profile_injection_and_unplanned_profile(self):
        bad = envelope()
        bad["verification_profiles"] = ["python-tooling-tests", "rm -rf /"]
        with self.assertRaises(ContractValidationError):
            validate_envelope(bad)
        bad_result = result_for()
        bad_result["verification_requests"] = [
            {"profile": "arbitrary-shell", "rationale": "run this command"}
        ]
        with self.assertRaises(ContractValidationError):
            validate_result(bad_result, envelope())

    def test_reject_command_or_url_as_patch_reference(self):
        for ref in ("https://example.com/patch", "file:///tmp/patch", "git apply patch.diff",
                    "artifact:sha256:not-a-digest"):
            bad = result_for()
            bad["patch_ref"] = ref
            with self.subTest(ref=ref), self.assertRaises(ContractValidationError):
                validate_result(bad, envelope())

    def test_reject_mismatched_task_or_contract_in_result(self):
        for field, value in (("task_id", "other-task"), ("contract_version", "2.0")):
            bad = result_for()
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ContractValidationError):
                validate_result(bad, envelope())

    def test_reject_patch_for_noncompleted_status_and_missing_patch_for_completed(self):
        bad = result_for()
        bad["status"] = "blocked"
        with self.assertRaises(ContractValidationError):
            validate_result(bad, envelope())
        bad = result_for()
        bad["patch_ref"] = None
        with self.assertRaises(ContractValidationError):
            validate_result(bad, envelope())

    def test_reject_unknown_status_and_invalid_assumption_confidence(self):
        bad = result_for()
        bad["status"] = "review_ready"
        with self.assertRaises(ContractValidationError):
            validate_result(bad, envelope())
        bad = result_for()
        bad["assumptions"][0]["confidence"] = "certain"
        with self.assertRaises(ContractValidationError):
            validate_result(bad, envelope())

    def test_context_documents_must_include_hash_matched_bounded_text(self):
        bad = envelope()
        bad["project_context"][0]["content"] = "tampered instructions"
        with self.assertRaises(ContractValidationError):
            validate_envelope(bad)

        bad = envelope()
        del bad["source_context"][0]["content"]
        with self.assertRaises(ContractValidationError):
            validate_envelope(bad)

        bad = envelope()
        bad["source_context"][0]["content"] = "x" * 256_001
        bad["source_context"][0]["sha256"] = hashlib.sha256(
            bad["source_context"][0]["content"].encode()
        ).hexdigest()
        with self.assertRaises(ContractValidationError):
            validate_envelope(bad)

    def test_context_documents_reject_duplicate_paths(self):
        bad = envelope()
        bad["project_context"].append(copy.deepcopy(bad["project_context"][0]))
        with self.assertRaises(ContractValidationError):
            validate_envelope(bad)

    def test_reject_stale_or_missing_context_fingerprints(self):
        for fingerprints in (
            [{"path": "AGENTS.md", "sha256": SHA_B}],
            [{"path": "AGENTS.md", "sha256": SHA_A},
             {"path": "lib/main.dart", "sha256": SHA_C}],
        ):
            bad = result_for()
            bad["context_fingerprints"] = fingerprints
            with self.assertRaises(ContractValidationError):
                validate_result(bad, envelope())

    def test_reject_usage_over_budget_and_boolean_integer(self):
        for key, value in (("tokens", 30001), ("patch_bytes", 200001),
                           ("tool_calls", True), ("wall_seconds", -1)):
            bad = result_for()
            bad["usage"][key] = value
            with self.subTest(key=key), self.assertRaises(ContractValidationError):
                validate_result(bad, envelope())

    def test_reject_test_paths_that_are_protected_or_unsafe(self):
        for path in ("../bad.py", ".env", "android/key.properties"):
            bad = result_for()
            bad["tests_added_or_changed"][0]["path"] = path
            with self.assertRaises(ContractValidationError):
                validate_result(bad, envelope())

    def test_reject_duplicate_json_keys_malformed_json_and_non_object_root(self):
        for raw in ('{"x":1,"x":2}', '{"broken":', '[]'):
            with self.subTest(raw=raw), self.assertRaises(ContractValidationError):
                parse_json_object(raw)

    def test_reject_oversized_json(self):
        with self.assertRaises(ContractValidationError):
            parse_json_object(" " * 1_000_001)

    def test_needs_clarification_has_no_patch_and_no_changed_paths(self):
        env = envelope()
        bad = result_for(env)
        bad.update(status="needs_clarification", patch_ref=None, changed_paths=[])
        self.assertEqual(validate_result(bad, env)["status"], "needs_clarification")


if __name__ == "__main__":
    unittest.main()
