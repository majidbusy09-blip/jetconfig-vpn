import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.project_artifact_namespace import workflow_artifact_name
from tools.task_orchestrator.workflow_artifact_names import (
    LEGACY_CODE_INDEX_NAME,
    LEGACY_SEMANTIC_AST_NAME,
    WorkflowArtifactNameError,
    resolve_artifact_names,
    write_github_output,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "docs/PROJECT_MANIFEST_SCHEMA.json").read_text(encoding="utf-8"))
REVISION = "a" * 40
METADATA = {
    "id": 1349356614,
    "full_name": "majidbusy09-blip/jetconfig-vpn",
    "html_url": "https://github.com/majidbusy09-blip/jetconfig-vpn",
    "default_branch": "main",
}


class WorkflowArtifactNameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "PROJECT_MANIFEST_SCHEMA.json").write_text(
            json.dumps(SCHEMA), encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self, manifest=None, *, directory="jet-project"):
        value = copy.deepcopy(manifest if manifest is not None else SCHEMA["examples"][0])
        value["project_id"] = directory
        value["repository"].update({
            "repository_id": str(METADATA["id"]),
            "full_name": METADATA["full_name"],
            "url": METADATA["html_url"],
            "default_branch": METADATA["default_branch"],
        })
        path = self.root / "docs" / "projects" / directory / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return value

    def resolve(self, *, metadata=None, expected=REVISION, checked_out=REVISION):
        return resolve_artifact_names(
            self.root,
            repository_metadata=metadata or METADATA,
            expected_source_revision=expected,
            checked_out_revision=checked_out,
        )

    def test_missing_matching_manifest_preserves_exact_legacy_names(self):
        names = self.resolve()
        self.assertEqual(names, {
            "semantic_ast": LEGACY_SEMANTIC_AST_NAME,
            "code_index": LEGACY_CODE_INDEX_NAME,
            "identity_mode": "v1",
        })

    def test_matching_manifest_generates_deterministic_project_and_source_bound_names(self):
        manifest = self.write_manifest()
        first = self.resolve()
        second = self.resolve()
        self.assertEqual(first, second)
        self.assertEqual(first["identity_mode"], "v2")
        binding = {
            "project_id": manifest["project_id"],
            "repository_id": str(METADATA["id"]),
            "repository_full_name": METADATA["full_name"],
            "default_branch": METADATA["default_branch"],
            "manifest_schema_version": manifest["schema_version"],
            "manifest_sha256": __import__(
                "tools.task_orchestrator.project_registry",
                fromlist=["manifest_digest"],
            ).manifest_digest(manifest),
        }
        self.assertEqual(first["semantic_ast"], workflow_artifact_name(
            LEGACY_SEMANTIC_AST_NAME,
            project_binding=binding,
            source_revision=REVISION,
        ))
        self.assertEqual(first["code_index"], workflow_artifact_name(
            LEGACY_CODE_INDEX_NAME,
            project_binding=binding,
            source_revision=REVISION,
        ))
        self.assertIn(str(METADATA["id"]), first["semantic_ast"])
        self.assertIn(REVISION, first["code_index"])

    def test_invalid_matching_manifest_fails_closed_instead_of_using_v1_names(self):
        manifest = self.write_manifest()
        manifest["repository"]["default_branch"] = "trunk"
        path = self.root / "docs" / "projects" / "jet-project" / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        metadata = dict(METADATA, default_branch="main")
        with self.assertRaises(WorkflowArtifactNameError):
            self.resolve(metadata=metadata)

    def test_repository_id_or_name_mismatch_is_not_silently_accepted(self):
        self.write_manifest()
        metadata = dict(
            METADATA,
            full_name="someone/else",
            html_url="https://github.com/someone/else",
        )
        with self.assertRaises(WorkflowArtifactNameError):
            self.resolve(metadata=metadata)

    def test_duplicate_matching_manifests_fail_closed(self):
        self.write_manifest(directory="jet-project")
        self.write_manifest(directory="second-project")
        with self.assertRaises(WorkflowArtifactNameError):
            self.resolve()

    def test_malformed_matching_manifest_fails_closed(self):
        manifest = self.write_manifest()
        manifest["repository"]["repository_id"] = "not-numeric"
        path = self.root / "docs" / "projects" / "jet-project" / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(WorkflowArtifactNameError):
            self.resolve()

    def test_source_revision_drift_fails_closed(self):
        self.write_manifest()
        with self.assertRaises(WorkflowArtifactNameError):
            self.resolve(checked_out="b" * 40)

    def test_retired_manifest_cannot_publish_project_scoped_artifacts(self):
        manifest = self.write_manifest()
        manifest["lifecycle"] = "retired"
        path = self.root / "docs" / "projects" / "jet-project" / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(WorkflowArtifactNameError):
            self.resolve()

    def test_github_output_is_fixed_single_line_and_rejects_symlink(self):
        names = self.resolve()
        output = self.root / "github_output"
        output.write_text("", encoding="utf-8")
        write_github_output(output, names)
        self.assertIn("semantic_ast=" + LEGACY_SEMANTIC_AST_NAME, output.read_text())

        unsafe = dict(names, code_index="safe\n::warning::injected")
        with self.assertRaises(WorkflowArtifactNameError):
            write_github_output(output, unsafe)

        target = self.root / "target"
        target.write_text("", encoding="utf-8")
        link = self.root / "output_link"
        link.symlink_to(target)
        with self.assertRaises(WorkflowArtifactNameError):
            write_github_output(link, names)


if __name__ == "__main__":
    unittest.main()
