from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.impact_analyzer import ImpactAnalysisError, analyze_impact


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False, shell=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class VerifiedImpactAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        git(self.root, "init", "-b", "feature/impact")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Impact Test")
        (self.root / "lib").mkdir()
        (self.root / "lib/vpn.dart").write_text("void connectVpn() {}\n", encoding="utf-8")
        (self.root / "lib/payment.dart").write_text("void createPayment() {}\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "impact fixture")
        self.base = git(self.root, "rev-parse", "HEAD")
        self.files = [
            {"path": "lib/vpn.dart", "git_blob_sha": git(self.root, "rev-parse", f"{self.base}:lib/vpn.dart"), "error_count": 0},
            {"path": "lib/payment.dart", "git_blob_sha": git(self.root, "rev-parse", f"{self.base}:lib/payment.dart"), "error_count": 0},
        ]
        self.index = {
            "schema_version": 2, "analysis_mode": "dart_analyzer_resolved_elements_multi_file",
            "source": {"file_count": 2, "files": self.files},
            "declarations": [
                {"id": "vpn-connect", "source_path": "lib/vpn.dart", "name": "connectVpn", "display_name": "connectVpn", "kind": "function"},
                {"id": "payment-create", "source_path": "lib/payment.dart", "name": "createPayment", "display_name": "createPayment", "kind": "function"},
            ],
            "call_sites": [
                {"source_path": "lib/payment.dart", "target_name": "connectVpn", "target_source_path": "lib/vpn.dart"},
                {"source_path": "lib/vpn.dart", "target_name": "reconnect"},
            ],
        }
        self.report = {
            "schema_version": 1, "analysis_mode": "static_reachability_from_curated_entrypoints",
            "source_file_count": 2, "source_files": self.files,
            "paths": [
                {"id": "vpn_recovery", "title": "VPN recovery", "description": "VPN connect and reconnect",
                 "reachable_declarations": [{"source_path": "lib/vpn.dart", "name": "connectVpn"}]},
                {"id": "payment", "title": "Payment", "description": "Payment lifecycle",
                 "reachable_declarations": [{"source_path": "lib/payment.dart", "name": "createPayment"}]},
            ],
        }
        self.index_path, self.report_path = self.root / "index.json", self.root / "critical.json"
        self.write_artifacts()
        self.task = {"task_id": "impact-task", "repository": {"base_sha": self.base},
                     "scope": {"allowed": ["lib/**"], "excluded": ["lib/generated/**"]}}

    def tearDown(self):
        self.temp.cleanup()

    def write_artifacts(self):
        self.index_path.write_text(json.dumps(self.index), encoding="utf-8")
        self.report_path.write_text(json.dumps(self.report), encoding="utf-8")

    def analyze(self, paths):
        return analyze_impact(root=self.root, task_record=self.task, changed_paths=paths,
                              resolved_index_path=self.index_path, critical_paths_path=self.report_path)

    def test_maps_changed_file_to_declarations_critical_paths_and_incoming_calls(self):
        result = self.analyze(["lib/vpn.dart"])
        self.assertEqual(result["impacted_critical_paths"][0]["id"], "vpn_recovery")
        self.assertEqual(result["changed_declarations"][0]["name"], "connectVpn")
        self.assertEqual(len(result["call_sites_in_changed_files"]), 1)
        self.assertEqual(len(result["call_sites_targeting_changed_declarations"]), 1)
        self.assertIn("flutter-analysis", result["recommended_verification_profiles"])

    def test_unindexed_changed_file_is_unknown_not_unaffected(self):
        result = self.analyze(["lib/new_feature.dart"])
        self.assertEqual(result["not_indexed_or_unknown"][0]["reason"], "not_present_in_semantic_index")
        self.assertIn("semantic_coverage_incomplete_for_one_or_more_changed_paths", result["risk_flags"])

    def test_non_dart_path_is_explicitly_unknown(self):
        result = self.analyze(["android/app/src/main/AndroidManifest.xml"])
        self.assertEqual(result["not_indexed_or_unknown"][0]["reason"], "outside_indexed_dart_source")

    def test_scope_violation_is_reported_not_hidden(self):
        result = self.analyze(["lib/vpn.dart", "docs/outside.md"])
        self.assertEqual(result["scope_violations"], ["docs/outside.md"])
        self.assertIn("changed_paths_outside_declared_task_scope", result["risk_flags"])

    def test_stale_changed_file_fingerprint_blocks_analysis(self):
        self.index["source"]["files"][0]["git_blob_sha"] = "0" * 40
        self.report["source_files"] = self.index["source"]["files"]
        self.write_artifacts()
        with self.assertRaises(ImpactAnalysisError):
            self.analyze(["lib/vpn.dart"])

    def test_mixed_artifact_manifests_are_rejected(self):
        self.report["source_files"] = self.report["source_files"][:1]
        self.write_artifacts()
        with self.assertRaises(ImpactAnalysisError):
            self.analyze(["lib/vpn.dart"])

    def test_duplicate_changed_paths_are_deduplicated_deterministically(self):
        self.assertEqual(self.analyze(["lib/vpn.dart", "lib/vpn.dart"]), self.analyze(["lib/vpn.dart"]))

    def test_unsafe_changed_path_is_rejected(self):
        with self.assertRaises(ImpactAnalysisError):
            self.analyze(["../secrets.txt"])

    def test_v2_artifacts_must_match_task_project_manifest_and_source(self):
        binding = {
            "project_id": "fixture-app",
            "repository_id": "123456",
            "repository_full_name": "owner/fixture-app",
            "default_branch": "main",
            "manifest_schema_version": 1,
            "manifest_sha256": "a" * 64,
            "base_sha": self.base,
        }
        self.task["github_project_binding"] = binding
        self.index["project_binding"] = binding
        self.index["source_revision"] = self.base
        self.report["project_binding"] = binding
        self.report["source_revision"] = self.base
        self.write_artifacts()
        result = self.analyze(["lib/vpn.dart"])
        self.assertEqual(result["source_revision"], self.base)

        self.report["source_revision"] = "f" * 40
        self.write_artifacts()
        with self.assertRaises(ImpactAnalysisError):
            self.analyze(["lib/vpn.dart"])

        self.report["source_revision"] = self.base
        self.index["project_binding"] = dict(binding, repository_id="999999")
        self.write_artifacts()
        with self.assertRaises(ImpactAnalysisError):
            self.analyze(["lib/vpn.dart"])

    def test_legacy_task_cannot_consume_v2_artifacts(self):
        self.index["project_binding"] = {"project_id": "fixture-app"}
        self.index["source_revision"] = self.base
        self.report["project_binding"] = {"project_id": "fixture-app"}
        self.report["source_revision"] = self.base
        self.write_artifacts()
        with self.assertRaises(ImpactAnalysisError):
            self.analyze(["lib/vpn.dart"])


if __name__ == "__main__":
    unittest.main()
