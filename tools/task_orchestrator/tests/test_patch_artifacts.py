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


if __name__ == "__main__":
    unittest.main()
