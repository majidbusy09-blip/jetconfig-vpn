import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.patch_artifacts import (
    LocalPatchArtifactStore,
    PatchArtifactError,
)
from tools.task_orchestrator.tests.test_patch_pipeline import (
    completed_result,
    patch_text,
)
from tools.task_orchestrator.tests.test_agent_contract import envelope


class PatchArtifactStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = LocalPatchArtifactStore(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_store_and_load_preserves_exact_bytes(self):
        patch = patch_text()
        ref = self.store.store_patch(patch)
        self.assertEqual(ref, "artifact:sha256:" + hashlib.sha256(patch.encode()).hexdigest())
        self.assertEqual(self.store.load_patch(ref), patch)

    def test_store_is_idempotent_for_same_content(self):
        patch = patch_text()
        self.assertEqual(self.store.store_patch(patch), self.store.store_patch(patch))

    def test_validates_loaded_artifact_against_result_and_scope(self):
        env = envelope()
        patch = patch_text()
        result = completed_result(env, patch)
        self.store.store_patch(patch)
        validated = self.store.validate_result_patch(result, env)
        self.assertEqual(validated["status"], "validated_for_human_review")
        self.assertFalse(validated["applied"])

    def test_rejects_tampered_artifact(self):
        patch = patch_text()
        ref = self.store.store_patch(patch)
        digest = ref.split(":")[-1]
        (self.root / (digest + ".patch")).write_text(patch + "# changed", encoding="utf-8")
        with self.assertRaises(PatchArtifactError):
            self.store.load_patch(ref)

    def test_rejects_missing_artifact(self):
        ref = "artifact:sha256:" + ("a" * 64)
        with self.assertRaises(PatchArtifactError):
            self.store.load_patch(ref)

    def test_rejects_symlink_artifact(self):
        patch = patch_text()
        ref = "artifact:sha256:" + hashlib.sha256(patch.encode()).hexdigest()
        digest = ref.split(":")[-1]
        outside = self.root / "outside"
        outside.write_text(patch, encoding="utf-8")
        target = self.root / (digest + ".patch")
        try:
            target.symlink_to(outside)
        except OSError:
            self.skipTest("symlink creation unavailable")
        with self.assertRaises(PatchArtifactError):
            self.store.load_patch(ref)

    def test_rejects_invalid_reference(self):
        for ref in ("../escape", "artifact:sha256:" + ("A" * 64), "artifact:sha256:short"):
            with self.subTest(ref=ref), self.assertRaises(PatchArtifactError):
                self.store.load_patch(ref)

    def test_rejects_oversized_artifact(self):
        small_store = LocalPatchArtifactStore(self.root, max_bytes=8)
        with self.assertRaises(PatchArtifactError):
            small_store.store_patch("x" * 9)

    def test_rejects_symlink_root(self):
        link = self.root / "root-link"
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation unavailable")
        with self.assertRaises(PatchArtifactError):
            LocalPatchArtifactStore(link)


    def test_project_scoped_stores_use_distinct_identity_and_source_directories(self):
        binding = {
            "project_id": "alpha-app",
            "repository_id": "123456",
            "repository_full_name": "owner/alpha-app",
            "default_branch": "main",
            "manifest_schema_version": 1,
            "manifest_sha256": "a" * 64,
            "base_sha": "b" * 40,
        }
        other = dict(binding, project_id="beta-app", repository_id="654321",
                     repository_full_name="owner/beta-app", manifest_sha256="c" * 64)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store_a = LocalPatchArtifactStore(root, project_binding=binding, source_revision="b" * 40)
            store_b = LocalPatchArtifactStore(root, project_binding=other, source_revision="b" * 40)
            patch = patch_text()
            ref_a = store_a.store_patch(patch)
            ref_b = store_b.store_patch(patch)
            self.assertEqual(ref_a, ref_b)
            self.assertNotEqual(store_a.root, store_b.root)
            self.assertTrue(store_a.load_patch(ref_a))
            with self.assertRaises(PatchArtifactError):
                store_a.assert_namespace(other, "b" * 40)
            with self.assertRaises(PatchArtifactError):
                store_a.assert_namespace(binding, "d" * 40)

    def test_rejects_root_replaced_by_symlink_after_initialization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store_root = root / "store"
            outside = root / "outside"
            store_root.mkdir()
            outside.mkdir()
            store = LocalPatchArtifactStore(store_root)
            saved = root / "store-saved"
            store_root.rename(saved)
            try:
                store_root.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(PatchArtifactError):
                store.store_patch(patch_text())
            self.assertEqual(list(outside.iterdir()), [])

    def test_rejects_project_namespace_replaced_by_symlink_after_initialization(self):
        binding = {
            "project_id": "alpha-app",
            "repository_id": "123456",
            "repository_full_name": "owner/alpha-app",
            "default_branch": "main",
            "manifest_schema_version": 1,
            "manifest_sha256": "a" * 64,
            "base_sha": "b" * 40,
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = LocalPatchArtifactStore(root, project_binding=binding, source_revision="b" * 40)
            projects = root / "projects"
            namespace = projects / "alpha-app"
            outside = root / "outside"
            outside.mkdir()
            saved = projects / "alpha-app-saved"
            namespace.rename(saved)
            try:
                namespace.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(PatchArtifactError):
                store.store_patch(patch_text())
            self.assertEqual(list(outside.iterdir()), [])

    def test_legacy_store_root_remains_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = LocalPatchArtifactStore(root)
            self.assertEqual(store.root, root.resolve())
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
