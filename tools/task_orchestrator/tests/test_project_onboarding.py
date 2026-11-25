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
            target_memory_pr_merged=True,
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


    def test_live_hesabgar_candidate_report_is_needs_review_not_active(self):
        target_sha = "177eb1a1f0ae8ae5a77a2c1c136804dff042d5db"
        existing_jet = json.loads(
            (ROOT / "docs/projects/jet-vpn-android/manifest.json").read_text(encoding="utf-8")
        )
        evidence = {
            "AGENTS.md": ("9295b5b5680ff2bd55ee9ab35c0a7d190798aa7e", 2523),
            "docs/PROJECT_CONTEXT.md": ("018781c137816c1610b69aa44a76dbadf12fe7da", 2901),
            "docs/CURRENT_STATUS.md": ("e4d66480e0660c59c67c1258834c1eb36dc15005", 1748),
            "docs/NEXT_STEPS.md": ("315e99144cd64e6cbef6d83d848da82c638a3211", 1898),
            "docs/DEVELOPMENT_LOG.md": ("a8313a17d24879e561f07263354482ee2f9d691c", 877),
        }
        inventory = {
            path: {
                "tracked": True,
                "regular_file": True,
                "blob_sha": blob_sha,
                "source_sha": target_sha,
                "size_bytes": size,
            }
            for path, (blob_sha, size) in evidence.items()
        }
        report = self.report(
            base_sha=target_sha,
            existing_manifests=[existing_jet],
            memory_inventory=inventory,
            toolchain_evidence={
                "flutter": {"verified": True, "version": "3.27.4", "source": "run 45562750263"},
                "dart": {"verified": True, "version": "3.6.2", "source": "run 45562750263"},
            },
            runner_results={"flutter-analysis": "success", "flutter-tests": "success"},
            source_index_assessment={"status": "adapter_required"},
            target_memory_pr_merged=False,
            dependency_lockfile_present=False,
        )
        self.assertEqual(report["overall_readiness"], "NEEDS_REVIEW")
        self.assertEqual(report["blockers"], [])
        self.assertEqual(report["discovery"]["memory"]["total_bytes"], 9947)
        self.assertEqual(len(report["discovery"]["memory"]["required_documents_found"]), 5)
        self.assertTrue(report["repository"]["identity_verified"])
        self.assertFalse(report["implementation_eligible"])
        self.assertEqual(report["manifest_validation"]["lifecycle"], "registered")


if __name__ == "__main__":
    unittest.main()
