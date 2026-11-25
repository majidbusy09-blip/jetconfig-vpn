import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.project_artifact_namespace import (
    ProjectArtifactNamespaceError,
    audit_record_path,
    cache_relative_path,
    cache_key,
    ensure_namespace_directory,
    index_output_paths,
    namespaced_relative_path,
    namespace_segments,
    verify_store_namespace,
    workflow_artifact_name,
)

PROJECT_A = {
    "project_id": "alpha-app",
    "repository_id": "123456",
    "repository_full_name": "owner/alpha-app",
    "default_branch": "main",
    "manifest_schema_version": 1,
    "manifest_sha256": "a" * 64,
}
PROJECT_B = {
    **PROJECT_A,
    "project_id": "beta-app",
    "repository_id": "654321",
    "repository_full_name": "owner/beta-app",
    "manifest_sha256": "b" * 64,
}
REVISION_A = "1" * 40
REVISION_B = "2" * 40


class ProjectArtifactNamespaceTests(unittest.TestCase):
    def test_v1_paths_and_artifact_names_remain_unchanged(self):
        self.assertEqual(
            index_output_paths(),
            {
                "resolved": "docs/generated/jet_vpn_resolved_index.json",
                "critical_paths": "docs/generated/jet_vpn_critical_paths.json",
                "semantic": "docs/generated/jet_vpn_semantic_index.json",
            },
        )
        self.assertEqual(namespaced_relative_path("patches", "patches/x.patch"), "patches/x.patch")
        self.assertEqual(cache_key("flutter-pub-cache"), "flutter-pub-cache")
        self.assertEqual(workflow_artifact_name("jet-vpn-code-index"), "jet-vpn-code-index")

    def test_v2_namespace_binds_project_repo_manifest_and_source(self):
        expected = ("alpha-app", "123456", "a" * 64, REVISION_A)
        self.assertEqual(namespace_segments(PROJECT_A, REVISION_A), expected)
        paths = index_output_paths(project_binding=PROJECT_A, source_revision=REVISION_A)
        self.assertEqual(
            paths["resolved"],
            "docs/generated/projects/alpha-app/123456/" + "a" * 64 + "/" + REVISION_A + "/indexes/resolved_index.json",
        )
        self.assertNotEqual(
            namespaced_relative_path("patches", "same.patch", project_binding=PROJECT_A, source_revision=REVISION_A),
            namespaced_relative_path("patches", "same.patch", project_binding=PROJECT_B, source_revision=REVISION_A),
        )
        self.assertNotEqual(
            namespaced_relative_path("patches", "same.patch", project_binding=PROJECT_A, source_revision=REVISION_A),
            namespaced_relative_path("patches", "same.patch", project_binding=PROJECT_A, source_revision=REVISION_B),
        )
        self.assertIn("/cache/flutter-pub-cache", cache_relative_path("flutter-pub-cache", project_binding=PROJECT_A, source_revision=REVISION_A))
        self.assertIn("/audit/run.json", audit_record_path("run.json", project_binding=PROJECT_A, source_revision=REVISION_A))

    def test_cache_key_and_workflow_name_include_full_identity(self):
        key_a = cache_key("dart-pub", project_binding=PROJECT_A, source_revision=REVISION_A)
        key_b = cache_key("dart-pub", project_binding=PROJECT_B, source_revision=REVISION_A)
        key_new_revision = cache_key("dart-pub", project_binding=PROJECT_A, source_revision=REVISION_B)
        self.assertTrue(key_a.startswith("v2:"))
        self.assertEqual(len(key_a), 67)
        self.assertNotEqual(key_a, key_b)
        self.assertNotEqual(key_a, key_new_revision)
        artifact = workflow_artifact_name("resolved-index", project_binding=PROJECT_A, source_revision=REVISION_A)
        self.assertIn("alpha-app", artifact)
        self.assertIn("123456", artifact)
        self.assertIn("a" * 64, artifact)
        self.assertIn(REVISION_A, artifact)

    def test_namespace_directory_isolated_and_reused_idempotently(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = ensure_namespace_directory(root, "patches", project_binding=PROJECT_A, source_revision=REVISION_A)
            b = ensure_namespace_directory(root, "patches", project_binding=PROJECT_B, source_revision=REVISION_A)
            self.assertNotEqual(a, b)
            self.assertEqual(a, ensure_namespace_directory(root, "patches", project_binding=PROJECT_A, source_revision=REVISION_A))
            self.assertTrue(a.is_dir())
            self.assertEqual((a.stat().st_mode & 0o777), 0o700)

    def test_rejects_symlink_namespace_component(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            (root / "projects").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ProjectArtifactNamespaceError):
                ensure_namespace_directory(root, "patches", project_binding=PROJECT_A, source_revision=REVISION_A)

    def test_rejects_manifest_or_revision_drift(self):
        bad = dict(PROJECT_A, manifest_sha256="not-a-digest")
        with self.assertRaises(ProjectArtifactNamespaceError):
            namespace_segments(bad, REVISION_A)
        with self.assertRaises(ProjectArtifactNamespaceError):
            namespace_segments(PROJECT_A, "short")
        with self.assertRaises(ProjectArtifactNamespaceError):
            namespace_segments(dict(PROJECT_A, base_sha=REVISION_B), REVISION_A)

    def test_rejects_unsafe_paths_and_categories(self):
        for path in ("../escape", "/absolute", "a\\b", "a/../b", ".hidden/file"):
            with self.subTest(path=path), self.assertRaises(ProjectArtifactNamespaceError):
                namespaced_relative_path("patches", path, project_binding=PROJECT_A, source_revision=REVISION_A)
        with self.assertRaises(ProjectArtifactNamespaceError):
            namespaced_relative_path("../patches", "x.patch", project_binding=PROJECT_A, source_revision=REVISION_A)

    def test_store_namespace_cannot_cross_projects_or_revisions(self):
        verify_store_namespace(PROJECT_A, REVISION_A, PROJECT_A, REVISION_A)
        with self.assertRaises(ProjectArtifactNamespaceError):
            verify_store_namespace(PROJECT_A, REVISION_A, PROJECT_B, REVISION_A)
        with self.assertRaises(ProjectArtifactNamespaceError):
            verify_store_namespace(PROJECT_A, REVISION_A, PROJECT_A, REVISION_B)
        with self.assertRaises(ProjectArtifactNamespaceError):
            verify_store_namespace(None, None, PROJECT_A, REVISION_A)
        with self.assertRaises(ProjectArtifactNamespaceError):
            verify_store_namespace(PROJECT_A, REVISION_A, None, REVISION_A)


if __name__ == "__main__":
    unittest.main()
