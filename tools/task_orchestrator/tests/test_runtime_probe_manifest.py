import json
import unittest
from pathlib import Path

from tools.task_orchestrator.sandbox_acceptance import REQUIRED_PROBES, SUITE_ID, SUITE_VERSION


MANIFEST_PATH = Path(__file__).resolve().parents[1] / "runtime_probe_manifest.json"
REQUIRED_FIELDS = {
    "probe_id", "evidence_owner", "evidence_type", "pass_criteria", "fail_closed",
    "independent_evidence_required", "provider_assertion_accepted_as_evidence",
    "guest_self_report_sufficient",
}


class RuntimeProbeManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_matches_signed_verifier_inventory_exactly(self):
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(self.manifest["suite_id"], SUITE_ID)
        self.assertEqual(self.manifest["suite_version"], SUITE_VERSION)
        ids = [probe["probe_id"] for probe in self.manifest["probes"]]
        self.assertEqual(len(ids), len(REQUIRED_PROBES))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), REQUIRED_PROBES)

    def test_manifest_is_explicitly_non_executable(self):
        self.assertEqual(self.manifest["status"], "specification_only_not_executable")
        self.assertIs(self.manifest["execution_enabled"], False)

    def test_every_probe_requires_independent_evidence(self):
        for probe in self.manifest["probes"]:
            with self.subTest(probe=probe["probe_id"]):
                self.assertEqual(set(probe), REQUIRED_FIELDS)
                self.assertTrue(probe["independent_evidence_required"])
                self.assertFalse(probe["provider_assertion_accepted_as_evidence"])
                self.assertFalse(probe["guest_self_report_sufficient"])
                for field in ("evidence_type", "pass_criteria", "fail_closed"):
                    self.assertIsInstance(probe[field], str)
                    self.assertTrue(probe[field].strip())

    def test_external_network_probes_have_external_observer(self):
        external = {
            "metadata_endpoint_blocked", "ipv4_egress_blocked", "ipv6_egress_blocked",
            "dns_udp_tcp_blocked", "quic_udp443_blocked", "external_canary_unreachable",
        }
        for probe in self.manifest["probes"]:
            if probe["probe_id"] in external:
                self.assertIn("external_canary", probe["evidence_owner"])


if __name__ == "__main__":
    unittest.main()
