import hashlib
import json
import unittest

from tools.task_orchestrator.sandbox_artifact_collector import (
    AcceptanceReference,
    ArtifactCandidate,
    ArtifactCollectionError,
    ArtifactCollectionPolicy,
    ArtifactCollector,
    evidence_bundle_digest,
)

ATTEMPT = "attempt-artifact-001"
RUNTIME = "runtime-fixture-001"
POLICY = "sha256:" + "a" * 64
EVIDENCE = "sha256:" + "b" * 64
REPORT = "sha256:" + "c" * 64


def policy(**changes):
    values = {
        "attempt_id": ATTEMPT,
        "runtime_id": RUNTIME,
        "policy_digest": POLICY,
        "evidence_digest": EVIDENCE,
        "acceptance_report_digest": REPORT,
        "allowed_roots": ("artifacts", "logs"),
        "retention_policy_id": "fixture-ephemeral",
        "retention_seconds": 3600,
    }
    values.update(changes)
    return ArtifactCollectionPolicy(**values)


def acceptance(**changes):
    values = {
        "status": "verified",
        "attempt_id": ATTEMPT,
        "runtime_id": RUNTIME,
        "policy_digest": POLICY,
        "evidence_digest": EVIDENCE,
        "report_digest": REPORT,
    }
    values.update(changes)
    return AcceptanceReference(**values)


class ArtifactCollectorTests(unittest.TestCase):
    def setUp(self):
        self.collector = ArtifactCollector(policy())

    def test_manifest_is_deterministic_sorted_and_bound_to_acceptance(self):
        items = [
            ArtifactCandidate("logs/stderr.txt", b"warning"),
            ArtifactCandidate("artifacts/report.bin", b"report-bytes"),
        ]
        first = self.collector.collect(acceptance=acceptance(), artifacts=items)
        second = self.collector.collect(acceptance=acceptance(), artifacts=reversed(items))
        self.assertEqual(first.canonical_bytes, second.canonical_bytes)
        self.assertEqual(first.sha256, hashlib.sha256(first.canonical_bytes).hexdigest())
        decoded = json.loads(first.canonical_bytes)
        self.assertEqual([item["path"] for item in decoded["artifacts"]], [
            "artifacts/report.bin", "logs/stderr.txt"
        ])
        self.assertEqual(decoded["artifact_count"], 2)
        self.assertEqual(decoded["total_bytes"], len(b"report-bytes") + len(b"warning"))
        self.assertFalse(decoded["execution_authorized"])
        self.assertFalse(decoded["eligible_for_untrusted_execution"])

    def test_digest_is_recomputed_from_exact_bytes(self):
        result = self.collector.collect(
            acceptance=acceptance(),
            artifacts=[ArtifactCandidate("artifacts/a.bin", b"actual bytes")],
        )
        entry = json.loads(result.canonical_bytes)["artifacts"][0]
        self.assertEqual(entry["sha256"], hashlib.sha256(b"actual bytes").hexdigest())

    def test_acceptance_binding_mismatch_fails_closed(self):
        for field, value in (
            ("status", "unverified"),
            ("attempt_id", "other-attempt"),
            ("runtime_id", "other-runtime"),
            ("policy_digest", "sha256:" + "d" * 64),
            ("evidence_digest", "sha256:" + "e" * 64),
            ("report_digest", "sha256:" + "f" * 64),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ArtifactCollectionError):
                    self.collector.collect(
                        acceptance=acceptance(**{field: value}),
                        artifacts=[ArtifactCandidate("artifacts/a.bin", b"x")],
                    )

    def test_absolute_traversal_windows_and_noncanonical_paths_rejected(self):
        for path in (
            "/artifacts/a", "../artifacts/a", "artifacts/../a", "artifacts//a",
            "artifacts/./a", "C:/artifacts/a", "artifacts\\a", "artifacts/a\x00b",
        ):
            with self.subTest(path=path):
                with self.assertRaises(ArtifactCollectionError):
                    self.collector.collect(
                        acceptance=acceptance(),
                        artifacts=[ArtifactCandidate(path, b"x")],
                    )

    def test_path_must_be_under_explicit_root(self):
        with self.assertRaisesRegex(ArtifactCollectionError, "outside"):
            self.collector.collect(
                acceptance=acceptance(),
                artifacts=[ArtifactCandidate("secrets/token", b"x")],
            )

    def test_symlinks_directories_devices_and_hardlinks_rejected(self):
        invalid = (
            ArtifactCandidate("artifacts/link", b"x", is_symlink=True),
            ArtifactCandidate("artifacts/dir", b"x", file_type="directory"),
            ArtifactCandidate("artifacts/device", b"x", file_type="character_device"),
            ArtifactCandidate("artifacts/hardlink", b"x", link_count=2),
        )
        for item in invalid:
            with self.subTest(item=item):
                with self.assertRaises(ArtifactCollectionError):
                    self.collector.collect(acceptance=acceptance(), artifacts=[item])

    def test_duplicate_paths_and_untyped_candidates_rejected(self):
        with self.assertRaisesRegex(ArtifactCollectionError, "Duplicate"):
            self.collector.collect(
                acceptance=acceptance(),
                artifacts=[
                    ArtifactCandidate("artifacts/a.bin", b"x"),
                    ArtifactCandidate("artifacts/a.bin", b"y"),
                ],
            )
        with self.assertRaises(ArtifactCollectionError):
            self.collector.collect(acceptance=acceptance(), artifacts=[{"path": "artifacts/a"}])

    def test_per_file_and_aggregate_limits_enforced(self):
        with self.assertRaisesRegex(ArtifactCollectionError, "per-file"):
            ArtifactCollector(policy(max_file_bytes=3)).collect(
                acceptance=acceptance(),
                artifacts=[ArtifactCandidate("artifacts/a", b"four")],
            )
        with self.assertRaisesRegex(ArtifactCollectionError, "aggregate"):
            ArtifactCollector(policy(max_total_bytes=3)).collect(
                acceptance=acceptance(),
                artifacts=[
                    ArtifactCandidate("artifacts/a", b"12"),
                    ArtifactCandidate("artifacts/b", b"34"),
                ],
            )

    def test_count_and_empty_inventory_limits_enforced(self):
        with self.assertRaises(ArtifactCollectionError):
            self.collector.collect(acceptance=acceptance(), artifacts=[])
        with self.assertRaises(ArtifactCollectionError):
            ArtifactCollector(policy(max_files=1)).collect(
                acceptance=acceptance(),
                artifacts=[
                    ArtifactCandidate("artifacts/a", b"a"),
                    ArtifactCandidate("artifacts/b", b"b"),
                ],
            )

    def test_policy_rejects_invalid_roots_digests_and_retention(self):
        for changes in (
            {"allowed_roots": ()},
            {"allowed_roots": ("../unsafe",)},
            {"allowed_roots": ("artifacts", "artifacts")},
            {"policy_digest": "not-a-digest"},
            {"retention_seconds": 1},
            {"retention_seconds": 31 * 24 * 60 * 60},
            {"max_files": 33},
            {"max_file_bytes": 2 * 1024 * 1024},
            {"max_total_bytes": 9 * 1024 * 1024},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(ArtifactCollectionError):
                    ArtifactCollector(policy(**changes))

    def test_evidence_digest_is_stable_and_content_sensitive(self):
        left = evidence_bundle_digest({"probe_b": b"B", "probe_a": b"A"})
        right = evidence_bundle_digest({"probe_a": b"A", "probe_b": b"B"})
        changed = evidence_bundle_digest({"probe_a": b"A", "probe_b": b"changed"})
        self.assertEqual(left, right)
        self.assertNotEqual(left, changed)
        self.assertTrue(left.startswith("sha256:"))

    def test_evidence_digest_rejects_empty_or_invalid_payloads(self):
        for value in ({}, {"probe": b""}, {"../probe": b"x"}):
            with self.subTest(value=value):
                with self.assertRaises(ArtifactCollectionError):
                    evidence_bundle_digest(value)


if __name__ == "__main__":
    unittest.main()
