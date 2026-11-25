from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.project_artifact_namespace import (
    ProjectArtifactNamespaceError,
    cache_key,
    index_output_paths,
    verify_store_namespace,
    workflow_artifact_name,
)
from tools.task_orchestrator.project_cache_store import ProjectScopedCacheStore
from tools.task_orchestrator.project_namespace import (
    lease_branch,
    lease_record_path,
    task_record_path,
    workspace_id,
)
from tools.task_orchestrator.github_issue_intake import build_intake
from tools.task_orchestrator.project_registry import (
    ProjectRegistryError,
    ensure_implementation_eligible,
    manifest_digest,
)

ROOT = Path(__file__).resolve().parents[3]
REVISION = "a" * 40
TASK_ID = "same-task-across-projects"


def load_binding(project_id: str) -> tuple[dict, dict]:
    manifest = json.loads(
        (ROOT / "docs" / "projects" / project_id / "manifest.json").read_text(encoding="utf-8")
    )
    repository = manifest["repository"]
    binding = {
        "project_id": manifest["project_id"],
        "repository_id": repository["repository_id"],
        "repository_full_name": repository["full_name"],
        "default_branch": repository["default_branch"],
        "manifest_schema_version": manifest["schema_version"],
        "manifest_sha256": manifest_digest(manifest),
    }
    return manifest, binding


JET_MANIFEST, JET_BINDING = load_binding("jet-vpn-android")
HESABGAR_MANIFEST, HESABGAR_BINDING = load_binding("hesabgar-man")


def canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def context_package(binding: dict) -> dict:
    package = {
        "schema_version": 2,
        "task_id": TASK_ID,
        "source_revision": REVISION,
        "project_binding": binding,
        "project_context": [],
        "source_context": [],
    }
    package["context_sha256"] = hashlib.sha256(canonical(package)).hexdigest()
    return package


class RealMultiProjectIsolationIntegrationTests(unittest.TestCase):
    def test_real_manifests_have_distinct_immutable_repository_bindings(self):
        self.assertEqual(JET_BINDING["repository_id"], "1349356614")
        self.assertEqual(HESABGAR_BINDING["repository_id"], "1423683236")
        self.assertNotEqual(JET_BINDING["project_id"], HESABGAR_BINDING["project_id"])
        self.assertNotEqual(JET_BINDING["manifest_sha256"], HESABGAR_BINDING["manifest_sha256"])

    def test_same_task_id_isolated_across_task_branch_lease_and_workspace(self):
        self.assertNotEqual(task_record_path(TASK_ID, JET_BINDING), task_record_path(TASK_ID, HESABGAR_BINDING))
        self.assertNotEqual(lease_branch(TASK_ID, JET_BINDING), lease_branch(TASK_ID, HESABGAR_BINDING))
        self.assertNotEqual(lease_record_path(TASK_ID, JET_BINDING), lease_record_path(TASK_ID, HESABGAR_BINDING))
        self.assertNotEqual(
            workspace_id(TASK_ID, REVISION, JET_BINDING),
            workspace_id(TASK_ID, REVISION, HESABGAR_BINDING),
        )

    def test_indexes_reports_cache_keys_and_workflow_artifacts_are_isolated(self):
        jet_paths = index_output_paths(project_binding=JET_BINDING, source_revision=REVISION)
        hesabgar_paths = index_output_paths(project_binding=HESABGAR_BINDING, source_revision=REVISION)
        self.assertTrue(all(jet_paths[key] != hesabgar_paths[key] for key in jet_paths))
        self.assertIn("/jet-vpn-android/1349356614/", jet_paths["resolved"])
        self.assertIn("/hesabgar-man/1423683236/", hesabgar_paths["resolved"])
        self.assertNotEqual(
            cache_key("context-v1", project_binding=JET_BINDING, source_revision=REVISION),
            cache_key("context-v1", project_binding=HESABGAR_BINDING, source_revision=REVISION),
        )
        self.assertNotEqual(
            workflow_artifact_name("resolved-index", project_binding=JET_BINDING, source_revision=REVISION),
            workflow_artifact_name("resolved-index", project_binding=HESABGAR_BINDING, source_revision=REVISION),
        )

    def test_store_namespace_rejects_cross_project_or_cross_revision_reads(self):
        verify_store_namespace(JET_BINDING, REVISION, JET_BINDING, REVISION)
        with self.assertRaises(ProjectArtifactNamespaceError):
            verify_store_namespace(JET_BINDING, REVISION, HESABGAR_BINDING, REVISION)
        with self.assertRaises(ProjectArtifactNamespaceError):
            verify_store_namespace(JET_BINDING, REVISION, JET_BINDING, "b" * 40)

    def test_context_cache_never_returns_another_projects_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ProjectScopedCacheStore(temporary)
            package = context_package(HESABGAR_BINDING)
            input_digest = "c" * 64
            store.put(
                "same-cache-name", package, project_binding=HESABGAR_BINDING,
                source_revision=REVISION, input_sha256=input_digest,
            )
            self.assertEqual(
                store.get(
                    "same-cache-name", project_binding=HESABGAR_BINDING,
                    source_revision=REVISION, input_sha256=input_digest,
                ),
                package,
            )
            self.assertIsNone(
                store.get(
                    "same-cache-name", project_binding=JET_BINDING,
                    source_revision=REVISION, input_sha256=input_digest,
                )
            )

    def test_real_hesabgar_manifest_accepts_read_only_intake_but_not_execution(self):
        schema = json.loads((ROOT / "docs" / "PROJECT_MANIFEST_SCHEMA.json").read_text(encoding="utf-8"))
        self.assertEqual(
            HESABGAR_BINDING["manifest_sha256"],
            "2b1dd1e9507d61c7dfdda7fd7d95d3ddbb39979d36d36aa3daa88d8a4dd17ece",
        )
        payload = {
            "schema_version": 2,
            "task_id": "live-intake-smoke-20261125",
            "goal": "Verify the read-only GitHub Issue intake packaging for Hesabgar. Do not modify repository files, create branches, open pull requests, claim a lease, or invoke an implementation agent.",
            "capability": "investigation",
            "risk": "low",
            "assigned_agent": "any",
            "allow": ["docs/CURRENT_STATUS.md"],
            "exclude": [".github/workflows", "android", "lib"],
            "scope_reason": "One-time operational smoke test of the registered project's read-only task intake path; no implementation or repository mutation is authorized.",
            "verification_profiles": ["flutter-analysis"],
            "project_binding": HESABGAR_BINDING,
        }
        ticks = chr(96) * 3
        body = chr(10).join([
            "<!-- jet-agent-task:v2 -->", "", ticks + "json",
            json.dumps(payload, indent=2), ticks,
        ])
        event = {
            "action": "opened",
            "repository": {
                "id": 1423683236,
                "full_name": "majidbusy09-blip/hesabgar_man",
                "html_url": "https://github.com/majidbusy09-blip/hesabgar_man",
                "default_branch": "main",
            },
            "issue": {
                "number": 17,
                "title": "[TEMPORARY] Verify read-only cross-repository task intake",
                "body": body,
                "state": "open",
                "html_url": "https://github.com/majidbusy09-blip/hesabgar_man/issues/17",
                "labels": [{"name": "agent-task"}],
            },
        }
        result = build_intake(
            event,
            project_schema=schema,
            project_manifests=[JET_MANIFEST, HESABGAR_MANIFEST],
        )
        self.assertEqual(result["project_binding"], HESABGAR_BINDING)
        self.assertEqual(result["project_lifecycle"], "registered")
        self.assertFalse(result["implementation_eligible"])
        self.assertEqual(result["execution"]["status"], "validated-awaiting-activation")
        self.assertFalse(result["execution"]["lease_claimed"])
        self.assertFalse(result["execution"]["agent_dispatched"])
        self.assertFalse(result["execution"]["model_called"])
        self.assertFalse(result["execution"]["source_uploaded"])
        self.assertIn(".github/workflows/agent-task-intake.yml", HESABGAR_MANIFEST["protected_paths"])

    def test_registered_projects_remain_blocked_from_implementation(self):
        for manifest in (JET_MANIFEST, HESABGAR_MANIFEST):
            with self.subTest(project=manifest["project_id"]):
                self.assertEqual(manifest["lifecycle"], "registered")
                with self.assertRaises(ProjectRegistryError):
                    ensure_implementation_eligible(manifest)
        self.assertEqual(HESABGAR_MANIFEST["source_index"]["strategy"], "none")


if __name__ == "__main__":
    unittest.main()
