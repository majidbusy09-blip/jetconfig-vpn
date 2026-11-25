from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.task_orchestrator.project_onboarding import build_readiness_report


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "docs/PROJECT_MANIFEST_SCHEMA.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ROOT / "docs/projects/hesabgar-man/manifest.json").read_text(encoding="utf-8"))
BASE_SHA = "a07992d3f4721fe1524bd093502f08171dafc92b"
REPOSITORY = {
    "id": 1423683236,
    "full_name": "majidbusy09-blip/hesabgar_man",
    "html_url": "https://github.com/majidbusy09-blip/hesabgar_man",
    "default_branch": "main",
}
AVAILABLE = {"python-tooling-tests", "flutter-analysis", "flutter-tests", "lexical-memory-audit"}
MEMORY = {
    path: {
        "tracked": True,
        "regular_file": True,
        "blob_sha": f"{index:040x}",
        "source_sha": BASE_SHA,
        "size_bytes": 1000,
    }
    for index, path in enumerate(MANIFEST["memory"]["required_documents"], start=1)
}
TOOLCHAINS = {
    "flutter": {"verified": True, "version": "3.27.4", "source": "GitHub Actions run"},
    "dart": {"verified": True, "version": "3.6.2", "source": "Flutter 3.27.4 CI toolchain"},
}


class ProjectOnboardingTests(unittest.TestCase):
    def report(self, **overrides):
        args = {
            "manifest": copy.deepcopy(MANIFEST),
            "schema": SCHEMA,
            "repository_metadata": dict(REPOSITORY),
            "base_sha": BASE_SHA,
            "existing_manifests": [
                {"project_id": "jet-vpn-android", "repository": {"repository_id": "1349356614"}}
            ],
            "available_profiles": AVAILABLE,
            "runner_results": {"flutter-analysis": "success", "flutter-tests": "success"},
            "memory_inventory": copy.deepcopy(MEMORY),
            "toolchain_evidence": copy.deepcopy(TOOLCHAINS),
            "source_index_assessment": {"status": "not_required", "reason": "Deferred to a separate generic Dart adapter."},
            "target_memory_pr_merged": True,
            "dependency_lockfile_present": True,
        }
        args.update(overrides)
        return build_readiness_report(**args)

    def test_complete_read_only_evidence_is_ready_for_registration_not_activation(self):
        report = self.report()
        self.assertEqual(report["overall_readiness"], "READY_FOR_REGISTRATION")
        self.assertFalse(report["writes_performed"])
        self.assertFalse(report["implementation_eligible"])
        self.assertTrue(report["repository"]["identity_verified"])
        self.assertEqual(report["manifest_validation"]["lifecycle"], "registered")

    def test_missing_required_memory_blocks_readiness(self):
        memory = copy.deepcopy(MEMORY)
        memory.pop("docs/NEXT_STEPS.md")
        report = self.report(memory_inventory=memory)
        self.assertEqual(report["overall_readiness"], "BLOCKED")
        self.assertIn("docs/NEXT_STEPS.md", report["discovery"]["memory"]["missing_documents"])

    def test_symlink_or_untracked_memory_is_not_accepted_as_evidence(self):
        memory = copy.deepcopy(MEMORY)
        memory["AGENTS.md"]["regular_file"] = False
        report = self.report(memory_inventory=memory)
        self.assertEqual(report["overall_readiness"], "BLOCKED")
        self.assertIn("AGENTS.md", report["discovery"]["memory"]["invalid_documents"])

    def test_memory_inventory_must_match_exact_pinned_revision(self):
        memory = copy.deepcopy(MEMORY)
        memory["AGENTS.md"]["source_sha"] = "b" * 40
        report = self.report(memory_inventory=memory)
        self.assertEqual(report["overall_readiness"], "BLOCKED")

    def test_identity_mismatch_blocks_readiness(self):
        metadata = dict(REPOSITORY)
        metadata["id"] = 999
        report = self.report(repository_metadata=metadata)
        self.assertEqual(report["overall_readiness"], "BLOCKED")
        self.assertFalse(report["repository"]["identity_verified"])

    def test_missing_fixed_runner_blocks_readiness(self):
        report = self.report(available_profiles={"python-tooling-tests"})
        self.assertEqual(report["overall_readiness"], "BLOCKED")

    def test_pending_ci_and_unmerged_target_pr_require_review(self):
        report = self.report(
            runner_results={"flutter-analysis": "pending", "flutter-tests": "success"},
            target_memory_pr_merged=False,
        )
        self.assertEqual(report["overall_readiness"], "NEEDS_REVIEW")
        self.assertTrue(any("successful run" in item for item in report["human_decisions"]))
        self.assertTrue(any("target-repository" in item for item in report["human_decisions"]))

    def test_unlocked_dependencies_and_project_specific_index_adapter_require_review(self):
        report = self.report(
            dependency_lockfile_present=False,
            source_index_assessment={"status": "adapter_required"},
        )
        self.assertEqual(report["overall_readiness"], "NEEDS_REVIEW")
        self.assertTrue(any("pubspec.lock" in item for item in report["human_decisions"]))
        self.assertTrue(any("Dart semantic indexing" in item for item in report["human_decisions"]))

    def test_malformed_base_sha_blocks_readiness(self):
        report = self.report(base_sha="main")
        self.assertEqual(report["overall_readiness"], "BLOCKED")

    def test_memory_byte_limit_is_enforced(self):
        memory = copy.deepcopy(MEMORY)
        memory["AGENTS.md"]["size_bytes"] = MANIFEST["memory"]["max_total_bytes"] + 1
        report = self.report(memory_inventory=memory)
        self.assertEqual(report["overall_readiness"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
