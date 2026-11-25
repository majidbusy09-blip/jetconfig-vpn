from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.task_orchestrator.project_registry import (
    ProjectRegistryError,
    ensure_implementation_eligible,
    loads_unique_json,
    manifest_digest,
    validate_manifest_schema,
    validate_project_manifest,
)


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "docs/PROJECT_MANIFEST_SCHEMA.json").read_text(encoding="utf-8"))
JET_VPN = copy.deepcopy(SCHEMA["examples"][0])
PYTHON = copy.deepcopy(SCHEMA["examples"][1])
JET_METADATA = {
    "id": 1349356614,
    "full_name": "majidbusy09-blip/jetconfig-vpn",
    "html_url": "https://github.com/majidbusy09-blip/jetconfig-vpn",
    "default_branch": "main",
}
IMPLEMENTED_PROFILES = {
    "python-tooling-tests", "flutter-analysis", "flutter-tests",
    "lexical-memory-audit",
}


class ProjectRegistryTests(unittest.TestCase):
    def validate_jet(self, manifest=None, *, metadata=None, existing=()):
        return validate_project_manifest(
            manifest or copy.deepcopy(JET_VPN),
            schema=SCHEMA,
            repository_metadata=metadata or JET_METADATA,
            existing_manifests=list(existing),
            available_profiles=IMPLEMENTED_PROFILES,
        )

    def test_checked_in_jet_vpn_example_passes_with_live_identity_and_fixed_profiles(self):
        result = self.validate_jet()
        self.assertEqual(result["project_id"], "jet-vpn-android")
        self.assertEqual(result["repository_id"], "1349356614")
        self.assertEqual(len(result["manifest_sha256"]), 64)
        self.assertFalse(result["implementation_eligible"])

    def test_python_example_is_schema_valid_but_runner_blocked(self):
        validate_manifest_schema(PYTHON, SCHEMA)
        metadata = {
            "id": 987654321,
            "full_name": "example-org/sample-python-service",
            "html_url": "https://github.com/example-org/sample-python-service",
            "default_branch": "main",
        }
        with self.assertRaisesRegex(ProjectRegistryError, "not implemented"):
            validate_project_manifest(
                PYTHON, schema=SCHEMA, repository_metadata=metadata,
                available_profiles=IMPLEMENTED_PROFILES,
            )

    def test_each_repository_identity_dimension_must_match(self):
        mutations = (
            ("id", 999999999),
            ("full_name", "someone/else"),
            ("html_url", "https://github.com/someone/else"),
            ("default_branch", "trunk"),
        )
        for key, value in mutations:
            metadata = dict(JET_METADATA)
            metadata[key] = value
            with self.subTest(key=key), self.assertRaises(ProjectRegistryError):
                self.validate_jet(metadata=metadata)

    def test_rejects_duplicate_project_id_and_repository_id_even_when_retired(self):
        for existing in (
            [{"project_id": "jet-vpn-android", "repository": {"repository_id": "999"}}],
            [{"project_id": "old-project", "lifecycle": "retired",
              "repository": {"repository_id": "1349356614"}}],
        ):
            with self.subTest(existing=existing), self.assertRaises(ProjectRegistryError):
                self.validate_jet(existing=existing)

    def test_every_non_active_lifecycle_is_ineligible(self):
        for lifecycle in ("registered", "paused", "retired"):
            manifest = copy.deepcopy(JET_VPN)
            manifest["lifecycle"] = lifecycle
            with self.subTest(lifecycle=lifecycle), self.assertRaisesRegex(
                ProjectRegistryError, "not active"
            ):
                ensure_implementation_eligible(manifest)
        active = copy.deepcopy(JET_VPN)
        active["lifecycle"] = "active"
        ensure_implementation_eligible(active)

    def test_valid_active_project_is_eligible(self):
        manifest = copy.deepcopy(JET_VPN)
        manifest["lifecycle"] = "active"
        result = self.validate_jet(manifest)
        self.assertTrue(result["implementation_eligible"])
        ensure_implementation_eligible(manifest)

    def test_rejects_unknown_manifest_fields_and_unsafe_paths(self):
        bad = copy.deepcopy(JET_VPN)
        bad["unexpected"] = "no"
        with self.assertRaises(ProjectRegistryError):
            self.validate_jet(bad)
        bad = copy.deepcopy(JET_VPN)
        bad["protected_paths"] = ["../secrets/token"]
        with self.assertRaises(ProjectRegistryError):
            self.validate_jet(bad)

    def test_rejects_bad_uri_and_unsupported_profile_declarations(self):
        bad = copy.deepcopy(JET_VPN)
        bad["repository"]["url"] = "not a uri"
        with self.assertRaises(ProjectRegistryError):
            self.validate_jet(bad)
        bad = copy.deepcopy(JET_VPN)
        bad["verification"]["required_profiles"] = ["python-tooling-tests"]
        bad["verification"]["supported_profiles"] = ["flutter-tests"]
        with self.assertRaisesRegex(ProjectRegistryError, "declared as supported"):
            self.validate_jet(bad)

    def test_rejects_remote_refs_unknown_schema_keywords_and_bad_schema_identity(self):
        bad_schema = copy.deepcopy(SCHEMA)
        bad_schema["properties"]["project_id"]["$ref"] = "https://example.com/schema.json"
        with self.assertRaises(ProjectRegistryError):
            validate_manifest_schema(JET_VPN, bad_schema)
        bad_schema = copy.deepcopy(SCHEMA)
        bad_schema["properties"]["project_id"]["x-eval"] = "anything"
        with self.assertRaisesRegex(ProjectRegistryError, "unsupported keyword"):
            validate_manifest_schema(JET_VPN, bad_schema)
        bad_schema = copy.deepcopy(SCHEMA)
        bad_schema["$id"] = "https://example.com/schema"
        with self.assertRaises(ProjectRegistryError):
            validate_manifest_schema(JET_VPN, bad_schema)
        bad_schema = copy.deepcopy(SCHEMA)
        bad_schema["properties"]["repository"]["properties"]["url"]["format"] = []
        with self.assertRaises(ProjectRegistryError):
            validate_manifest_schema(JET_VPN, bad_schema)

    def test_validates_optional_registration_date_time_format(self):
        manifest = copy.deepcopy(JET_VPN)
        manifest["metadata"] = {"registered_at": "2026-11-25T00:17:00Z"}
        self.validate_jet(manifest)
        manifest["metadata"]["registered_at"] = "2026-11-25T00:17:00"
        with self.assertRaises(ProjectRegistryError):
            self.validate_jet(manifest)

    def test_rejects_duplicate_json_keys_and_non_finite_numbers(self):
        for raw in ('{"project_id":"one","project_id":"two"}', '{"value":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ProjectRegistryError):
                loads_unique_json(raw)

    def test_manifest_digest_is_deterministic_and_mutation_sensitive(self):
        first = manifest_digest(JET_VPN)
        reordered = dict(reversed(list(JET_VPN.items())))
        self.assertEqual(first, manifest_digest(reordered))
        changed = copy.deepcopy(JET_VPN)
        changed["display_name"] += " updated"
        self.assertNotEqual(first, manifest_digest(changed))

    def test_malformed_existing_registry_record_fails_closed(self):
        with self.assertRaisesRegex(ProjectRegistryError, "malformed"):
            self.validate_jet(existing=[{"project_id": "old", "repository": None}])


if __name__ == "__main__":
    unittest.main()
