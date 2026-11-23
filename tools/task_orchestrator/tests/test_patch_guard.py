import unittest

from tools.task_orchestrator.agent_contract import CONTRACT_VERSION
from tools.task_orchestrator.patch_guard import (
    PatchValidationError,
    validate_patch_text,
)


def envelope():
    return {
        "contract_version": CONTRACT_VERSION,
        "task_id": "patch-guard-test",
        "goal": "Validate a proposed patch safely",
        "capability": "bug_fix",
        "risk": "low",
        "repository": {
            "name": "owner/repo",
            "branch": "feature/test",
            "base_sha": "a" * 64,
            "workspace_id": "workspace_123",
        },
        "scope": {
            "allowed_paths": ["tools/**"],
            "excluded_paths": ["tools/generated/**"],
            "scope_reason": "",
        },
        "project_context": [],
        "source_context": [],
        "semantic_context": {
            "status": "unavailable",
            "source_sha": None,
            "summary": "",
            "limitations": [],
        },
        "constraints": {
            "invariants": [],
            "prohibited_paths": [],
            "compatibility": [],
            "known_risks": [],
        },
        "budgets": {
            "max_wall_seconds": 60,
            "max_tokens": 1000,
            "max_tool_calls": 10,
            "max_changed_files": 5,
            "max_patch_bytes": 10000,
        },
        "verification_profiles": ["python-tooling-tests"],
    }


def diff(path="tools/example.py", body="+value = 1"):
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        "--- a/" + path + "\n"
        "+++ b/" + path + "\n"
        "@@ -1 +1 @@\n"
        "-value = 0\n"
        f"{body}\n"
    )


class PatchGuardTests(unittest.TestCase):
    def test_accepts_scoped_text_patch(self):
        result = validate_patch_text(diff(), envelope(), ["tools/example.py"])
        self.assertEqual(result["changed_paths"], ["tools/example.py"])
        self.assertEqual(result["file_count"], 1)

    def test_rejects_path_traversal(self):
        with self.assertRaises(PatchValidationError):
            validate_patch_text(diff("../outside.py"), envelope(), ["tools/example.py"])

    def test_rejects_out_of_scope_path(self):
        with self.assertRaises(PatchValidationError):
            validate_patch_text(diff("lib/main.dart"), envelope(), ["lib/main.dart"])

    def test_rejects_excluded_path(self):
        with self.assertRaises(PatchValidationError):
            validate_patch_text(diff("tools/generated/output.py"), envelope(), ["tools/generated/output.py"])

    def test_rejects_protected_path(self):
        with self.assertRaises(PatchValidationError):
            validate_patch_text(diff("tools/key.properties"), envelope(), ["tools/key.properties"])

    def test_rejects_binary_patch(self):
        with self.assertRaises(PatchValidationError):
            validate_patch_text(diff() + "GIT binary patch\n", envelope(), ["tools/example.py"])

    def test_rejects_rename(self):
        patch = (
            "diff --git a/tools/old.py b/tools/new.py\n"
            "similarity index 90%\nrename from tools/old.py\n"
            "rename to tools/new.py\n"
        )
        with self.assertRaises(PatchValidationError):
            validate_patch_text(patch, envelope(), ["tools/old.py"])

    def test_rejects_symlink_mode(self):
        patch = (
            "diff --git a/tools/link b/tools/link\n"
            "new file mode 120000\n"
            "--- /dev/null\n+++ b/tools/link\n"
            "@@ -0,0 +1 @@\n+target\n"
        )
        with self.assertRaises(PatchValidationError):
            validate_patch_text(patch, envelope(), ["tools/link"])

    def test_rejects_mismatched_file_header(self):
        patch = diff().replace("+++ b/tools/example.py", "+++ b/tools/other.py")
        with self.assertRaises(PatchValidationError):
            validate_patch_text(patch, envelope(), ["tools/example.py"])

    def test_rejects_patch_over_budget(self):
        env = envelope()
        env["budgets"]["max_patch_bytes"] = 10
        with self.assertRaises(PatchValidationError):
            validate_patch_text(diff(), env, ["tools/example.py"])

    def test_rejects_mismatch_with_agent_declared_paths(self):
        with self.assertRaises(PatchValidationError):
            validate_patch_text(diff(), envelope(), ["tools/another.py"])

    def test_does_not_misread_deleted_content_as_file_header(self):
        patch = diff(body="--- text content")
        result = validate_patch_text(patch, envelope(), ["tools/example.py"])
        self.assertEqual(result["changed_paths"], ["tools/example.py"])

    def test_rejects_combined_diff(self):
        patch = diff().replace("@@ -1 +1 @@", "@@@ -1,1 -1,1 +1,1 @@@")
        with self.assertRaises(PatchValidationError):
            validate_patch_text(patch, envelope(), ["tools/example.py"])

    def test_rejects_duplicate_file_headers(self):
        patch = diff().replace(
            "--- a/tools/example.py\n",
            "--- a/tools/example.py\n--- a/tools/example.py\n",
        )
        with self.assertRaises(PatchValidationError):
            validate_patch_text(patch, envelope(), ["tools/example.py"])

    def test_rejects_both_sides_as_dev_null(self):
        patch = diff().replace(
            "--- a/tools/example.py",
            "--- /dev/null",
        ).replace(
            "+++ b/tools/example.py",
            "+++ /dev/null",
        )
        with self.assertRaises(PatchValidationError):
            validate_patch_text(patch, envelope(), ["tools/example.py"])

    def test_rejects_malformed_hunk_header(self):
        patch = diff().replace("@@ -1 +1 @@", "@@ malformed @@")
        with self.assertRaises(PatchValidationError):
            validate_patch_text(patch, envelope(), ["tools/example.py"])

    def test_rejects_non_text_input(self):
        with self.assertRaises(PatchValidationError):
            validate_patch_text(b"not text", envelope(), ["tools/example.py"])

    def test_rejects_empty_patch(self):
        with self.assertRaises(PatchValidationError):
            validate_patch_text("", envelope(), ["tools/example.py"])


if __name__ == "__main__":
    unittest.main()
