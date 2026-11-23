import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.patch_review_command import (
    PatchReviewCommandError,
    _read_json_object,
)


class PatchReviewCommandInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_reads_regular_json_object(self):
        path = self.root / "input.json"
        path.write_text('{"task_id":"sample-task"}', encoding="utf-8")
        self.assertEqual(_read_json_object(path), {"task_id": "sample-task"})

    def test_rejects_duplicate_json_keys(self):
        path = self.root / "duplicate.json"
        path.write_text('{"task_id":"first","task_id":"second"}', encoding="utf-8")
        with self.assertRaises(PatchReviewCommandError):
            _read_json_object(path)

    def test_rejects_non_object_json(self):
        path = self.root / "array.json"
        path.write_text('[]', encoding="utf-8")
        with self.assertRaises(PatchReviewCommandError):
            _read_json_object(path)

    def test_rejects_symlink(self):
        target = self.root / "target.json"
        target.write_text('{"ok":true}', encoding="utf-8")
        link = self.root / "link.json"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks are unavailable on this platform.")
        with self.assertRaises(PatchReviewCommandError):
            _read_json_object(link)

    def test_rejects_oversized_input(self):
        path = self.root / "large.json"
        path.write_text(json.dumps({"payload": "x" * 100}), encoding="utf-8")
        with self.assertRaises(PatchReviewCommandError):
            _read_json_object(path, max_bytes=32)


if __name__ == "__main__":
    unittest.main()
