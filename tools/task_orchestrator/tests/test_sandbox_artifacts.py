import hashlib
import json
import unittest

from tools.task_orchestrator.sandbox_artifacts import (
    MAX_ARTIFACTS,
    MAX_ARTIFACT_BYTES,
    MAX_TOTAL_ARTIFACT_BYTES,
    ArtifactCandidate,
    ArtifactCollectionError,
    ArtifactCollector,
)


ATTEMPT = "attempt-artifact-001"
RUNTIME = "runtime-fixture-001"
POLICY = "a" * 64
EVIDENCE = "b" * 64
REPORT = "c" * 64


def collector(**changes):
    values = {
        "attempt_id": ATTEMPT,
        "runtime_id": RUNTIME,
        "policy_digest": POLICY,
        "evidence_digest": EVIDENCE,
        "acceptance_report_digest": REPORT,
    }
    values.update(changes)
    return ArtifactCollector(**values)


class ArtifactCollectorTests(unittest.TestCase):
    def test_manifest_is_deterministic_sorted_and_binds_attempt_evidence_and_report(self):
        first = collector().collect([
            ArtifactCandidate("reports/acceptance.json", "regular_file", b"report bytes"),
            ArtifactCandidate("artifacts/output.bin", "regular_file", b"artifact bytes"),
        ])
        second = collector().collect([
            ArtifactCandidate("artifacts/output.bin", "regular_file", b"artifact bytes"),
            ArtifactCandidate("reports/acceptance.json", "regular_file", b"report bytes"),
        ])
        self.assertEqual(first.canonical_bytes, second.canonical_bytes)
        self.assertEqual(first.manifest_sha256, hashlib.sha256(first.canonical_bytes).hexdigest())
        self.assertEqual([item.path for item in first.artifacts], [
            "artifacts/output.bin", "reports/acceptance.json"
        ])
        payload = json.loads(first.canonical_bytes)
        self.assertEqual(payload["attempt_id"], ATTEMPT)
        self.assertEqual(payload["runtime_id"], RUNTIME)
        self.assertEqual(payload["policy_digest"], POLICY)
        self.assertEqual(payload["evidence_digest"], EVIDENCE)
        self.assertEqual(payload["acceptance_report_digest"], REPORT)
        self.assertFalse(first.execution_authorized)
        self.assertFalse(first.eligible_for_untrusted_execution)

    def test_host_side_digest_is_recomputed_from_supplied_bytes(self):
        data = b"independent bytes"
        result = collector().collect([ArtifactCandidate("artifacts/result.dat", "regular_file", data)])
        self.assertEqual(result.artifacts[0].sha256, hashlib.sha256(data).hexdigest())
        self.assertEqual(result.artifacts[0].size_bytes, len(data))
        self.assertEqual(result.artifacts[0].content, data)

    def test_paths_outside_allowlist_or_with_traversal_are_rejected(self):
        for path in (
            "../artifacts/escape", "artifacts/../secret", "/artifacts/absolute",
            "C:/artifacts/windows", "artifacts//double", "artifacts/./dot",
            "private/secret", "artifacts\\windows", "artifacts/trailing/",
            "artifacts/.hidden", "artifacts/bad name", "artifacts/" + "x" * 241,
        ):
            with self.subTest(path=path):
                with self.assertRaises(ArtifactCollectionError):
                    collector().collect([ArtifactCandidate(path, "regular_file", b"x")])

    def test_symlink_directory_device_and_symlink_target_are_rejected(self):
        for kind, target in (
            ("symlink", "outside/secret"), ("directory", None), ("device", None),
            ("regular_file", "outside/secret"),
        ):
            with self.subTest(kind=kind, target=target):
                with self.assertRaises(ArtifactCollectionError):
                    collector().collect([
                        ArtifactCandidate("artifacts/item", kind, b"x", symlink_target=target)
                    ])

    def test_hardlinked_or_invalid_link_count_records_are_rejected(self):
        for link_count in (0, 2, -1, True, "1"):
            with self.subTest(link_count=link_count):
                with self.assertRaisesRegex(ArtifactCollectionError, "Hard-linked"):
                    collector().collect([
                        ArtifactCandidate("artifacts/linked", "regular_file", b"x", link_count=link_count)
                    ])

    def test_duplicate_paths_and_empty_content_are_rejected(self):
        with self.assertRaisesRegex(ArtifactCollectionError, "Duplicate"):
            collector().collect([
                ArtifactCandidate("artifacts/a.bin", "regular_file", b"a"),
                ArtifactCandidate("artifacts/a.bin", "regular_file", b"b"),
            ])
        with self.assertRaisesRegex(ArtifactCollectionError, "Empty"):
            collector().collect([ArtifactCandidate("artifacts/empty", "regular_file", b"")])

    def test_file_count_per_file_and_aggregate_limits_are_enforced(self):
        with self.assertRaisesRegex(ArtifactCollectionError, "At least one"):
            collector().collect([])
        with self.assertRaisesRegex(ArtifactCollectionError, "count"):
            collector().collect([
                ArtifactCandidate(f"artifacts/file-{i:02d}", "regular_file", b"x")
                for i in range(MAX_ARTIFACTS + 1)
            ])
        with self.assertRaisesRegex(ArtifactCollectionError, "per-file"):
            collector().collect([
                ArtifactCandidate("artifacts/large", "regular_file", b"x" * (MAX_ARTIFACT_BYTES + 1))
            ])
        too_many_bytes = (b"x" * MAX_ARTIFACT_BYTES,) * (MAX_TOTAL_ARTIFACT_BYTES // MAX_ARTIFACT_BYTES + 1)
        with self.assertRaisesRegex(ArtifactCollectionError, "aggregate"):
            collector().collect([
                ArtifactCandidate(f"artifacts/file-{i}", "regular_file", payload)
                for i, payload in enumerate(too_many_bytes)
            ])

    def test_malformed_candidate_types_and_metadata_fail_closed(self):
        with self.assertRaises(ArtifactCollectionError):
            collector().collect([{"path": "artifacts/a", "kind": "regular_file", "content": b"x"}])
        with self.assertRaises(ArtifactCollectionError):
            collector().collect([ArtifactCandidate("artifacts/a", "regular_file", "not-bytes")])
        for field, value in (
            ("attempt_id", "../attempt"), ("runtime_id", ""),
            ("policy_digest", "A" * 64), ("evidence_digest", "not-a-digest"),
            ("acceptance_report_digest", "d" * 63),
            ("retention_seconds", 0), ("retention_seconds", 30 * 24 * 60 * 60 + 1),
            ("retention_seconds", True),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ArtifactCollectionError):
                    collector(**{field: value})

    def test_retention_is_bounded_and_included_in_manifest(self):
        result = collector(retention_seconds=3600).collect([
            ArtifactCandidate("artifacts/output", "regular_file", b"x")
        ])
        self.assertEqual(result.retention_seconds, 3600)
        self.assertEqual(json.loads(result.canonical_bytes)["retention_seconds"], 3600)


if __name__ == "__main__":
    unittest.main()
