import hashlib
import unittest

from tools.task_orchestrator.patch_pipeline import (
    PatchPipelineError,
    validate_completed_patch,
)
from tools.task_orchestrator.tests.test_agent_contract import envelope, result_for


def patch_text():
    path = "tools/example.py"
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n+++ b/{path}\n"
        "@@ -1 +1 @@\n-value = 0\n+value = 1\n"
    )


def completed_result(env, patch):
    result = result_for(env)
    raw = patch.encode("utf-8")
    result["patch_ref"] = "artifact:sha256:" + hashlib.sha256(raw).hexdigest()
    result["usage"]["patch_bytes"] = len(raw)
    result["changed_paths"] = ["tools/example.py"]
    return result


class PatchPipelineTests(unittest.TestCase):
    def test_binds_exact_patch_to_validated_agent_result(self):
        env = envelope()
        patch = patch_text()
        result = completed_result(env, patch)
        summary = validate_completed_patch(result, env, patch)
        self.assertEqual(summary["status"], "validated_for_human_review")
        self.assertFalse(summary["applied"])
        self.assertEqual(summary["patch_validation"]["changed_paths"], ["tools/example.py"])

    def test_rejects_patch_digest_mismatch(self):
        env = envelope()
        patch = patch_text()
        result = completed_result(env, patch)
        with self.assertRaises(PatchPipelineError):
            validate_completed_patch(result, env, patch + "# tampered\n")

    def test_rejects_patch_size_mismatch(self):
        env = envelope()
        patch = patch_text()
        result = completed_result(env, patch)
        result["usage"]["patch_bytes"] += 1
        with self.assertRaises(PatchPipelineError):
            validate_completed_patch(result, env, patch)

    def test_rejects_out_of_scope_patch_even_with_matching_digest(self):
        env = envelope()
        patch = patch_text().replace("tools/example.py", "lib/main.dart")
        result = completed_result(env, patch)
        result["changed_paths"] = ["lib/main.dart"]
        with self.assertRaises(PatchPipelineError):
            validate_completed_patch(result, env, patch)

    def test_rejects_agent_path_claim_mismatch(self):
        env = envelope()
        patch = patch_text()
        result = completed_result(env, patch)
        result["changed_paths"] = ["tools/other.py"]
        with self.assertRaises(PatchPipelineError):
            validate_completed_patch(result, env, patch)

    def test_never_accepts_non_completed_result(self):
        env = envelope()
        patch = patch_text()
        result = completed_result(env, patch)
        result["status"] = "failed"
        with self.assertRaises(PatchPipelineError):
            validate_completed_patch(result, env, patch)


if __name__ == "__main__":
    unittest.main()
