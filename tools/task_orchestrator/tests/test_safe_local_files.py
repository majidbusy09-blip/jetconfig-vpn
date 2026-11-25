from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.safe_local_files import (
    SafeLocalFileError,
    atomic_write_bytes,
    ensure_directory,
    read_bytes,
    readlink,
    stat_entry,
)


class SafeLocalFileTests(unittest.TestCase):
    def test_atomic_create_read_and_replace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            atomic_write_bytes(root, ".agent/tasks/x/task.json", b"one", replace=False, create_parents=True)
            self.assertEqual(read_bytes(root, ".agent/tasks/x/task.json"), b"one")
            with self.assertRaises(SafeLocalFileError):
                atomic_write_bytes(root, ".agent/tasks/x/task.json", b"two", replace=False)
            atomic_write_bytes(root, ".agent/tasks/x/task.json", b"two", replace=True)
            self.assertEqual(read_bytes(root, ".agent/tasks/x/task.json"), b"two")

    def test_rejects_symlinked_parent_for_read_and_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            real = root / "real"
            real.mkdir()
            (real / "data.json").write_bytes(b"{}")
            link = root / "linked"
            try:
                link.symlink_to(real, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(SafeLocalFileError):
                read_bytes(root, "linked/data.json")
            with self.assertRaises(SafeLocalFileError):
                atomic_write_bytes(root, "linked/new.json", b"{}", replace=False)

    def test_rejects_symlinked_leaf(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root / "outside"
            outside.write_bytes(b"safe")
            link = root / "link"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(SafeLocalFileError):
                read_bytes(root, "link")
            with self.assertRaises(SafeLocalFileError):
                atomic_write_bytes(root, "link", b"unsafe", replace=True)
            self.assertEqual(outside.read_bytes(), b"safe")

    def test_rejects_root_replaced_by_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "root"
            outside = base / "outside"
            root.mkdir()
            outside.mkdir()
            saved = base / "saved"
            root.rename(saved)
            try:
                root.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(SafeLocalFileError):
                ensure_directory(root, ".agent/tasks")

    def test_stat_and_readlink_are_relative_and_do_not_follow_leaf(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target.txt"
            target.write_text("payload", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink creation unavailable")
            metadata = stat_entry(root, "link.txt")
            self.assertTrue(metadata is not None and metadata.st_mode & 0o170000 == 0o120000)
            self.assertEqual(readlink(root, "link.txt"), str(target))
            self.assertIsNone(stat_entry(root, "missing.txt"))

    def test_read_size_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "large.bin").write_bytes(b"x" * 16)
            with self.assertRaises(SafeLocalFileError):
                read_bytes(root, "large.bin", max_bytes=8)


if __name__ == "__main__":
    unittest.main()
