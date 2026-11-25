from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.task_orchestrator import project_cache_store as cache


SOURCE = "a" * 40
BINDING = {
    "project_id": "hesabgar-man",
    "repository_id": "1423683236",
    "repository_full_name": "majidbusy09-blip/hesabgar_man",
    "default_branch": "main",
    "manifest_schema_version": 1,
    "manifest_sha256": "b" * 64,
    "base_sha": SOURCE,
}
OTHER = dict(BINDING, project_id="other-project", repository_id="123456")
INPUT = "c" * 64


def package(binding=BINDING, source=SOURCE):
    body = {
        "schema_version": 2, "task_id": "cache-test", "source_revision": source,
        "project_binding": binding, "project_context": [], "source_context": [],
        "total_bytes": 0,
    }
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    body["context_sha256"] = hashlib.sha256(canonical).hexdigest()
    return body


class ProjectScopedCacheStoreTests(unittest.TestCase):
    def test_round_trip_and_project_namespace(self):
        with tempfile.TemporaryDirectory() as root:
            store = cache.ProjectScopedCacheStore(root)
            name = "context-v1-" + "d" * 64
            value = package()
            store.put(name, value, project_binding=BINDING, source_revision=SOURCE, input_sha256=INPUT)
            self.assertEqual(store.get(name, project_binding=BINDING, source_revision=SOURCE, input_sha256=INPUT), value)
            self.assertIsNone(store.get(name, project_binding=OTHER, source_revision=SOURCE, input_sha256=INPUT))

    def test_source_and_input_drift_are_cache_misses_not_cross_reads(self):
        with tempfile.TemporaryDirectory() as root:
            store = cache.ProjectScopedCacheStore(root)
            name = "context-v1-" + "e" * 64
            value = package()
            store.put(name, value, project_binding=BINDING, source_revision=SOURCE, input_sha256=INPUT)
            self.assertIsNone(store.get(name, project_binding=BINDING, source_revision="f" * 40, input_sha256=INPUT))
            self.assertIsNone(store.get(name, project_binding=BINDING, source_revision=SOURCE, input_sha256="9" * 64))

    def test_corrupt_entry_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            store = cache.ProjectScopedCacheStore(root)
            name = "context-v1-" + "1" * 64
            value = package()
            store.put(name, value, project_binding=BINDING, source_revision=SOURCE, input_sha256=INPUT)
            directory = Path(root) / "projects" / BINDING["project_id"] / BINDING["repository_id"] / BINDING["manifest_sha256"] / SOURCE / "cache"
            target = next(directory.glob("*.json"))
            target.write_text("{", encoding="utf-8")
            with self.assertRaises(cache.ProjectCacheError):
                store.get(name, project_binding=BINDING, source_revision=SOURCE, input_sha256=INPUT)

    def test_cached_builder_uses_cache_and_rebuilds_on_input_change(self):
        with tempfile.TemporaryDirectory() as root:
            value = package()
            kwargs = {
                "root": root, "task_id": "cache-test", "source_revision": SOURCE,
                "required_paths": [], "source_paths": [], "allowed_patterns": [],
                "excluded_patterns": [], "project_binding": BINDING,
                "memory_manifest_version": 1, "memory_manifest_max_total_bytes": 1024,
            }
            with patch.object(cache, "build_context", return_value=value) as builder:
                first = cache.build_context_cached(cache_root=root, **kwargs)
                second = cache.build_context_cached(cache_root=root, **kwargs)
                self.assertEqual(first, second)
                self.assertEqual(builder.call_count, 1)
                changed = dict(kwargs, source_paths=["lib/main.dart"])
                cache.build_context_cached(cache_root=root, **changed)
                self.assertEqual(builder.call_count, 2)


if __name__ == "__main__":
    unittest.main()
