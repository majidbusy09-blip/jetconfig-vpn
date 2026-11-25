import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.github_task_inbox import InboxError, ingest_artifact_bytes
from tools.task_orchestrator.project_registry import manifest_digest

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "docs/PROJECT_MANIFEST_SCHEMA.json").read_text(encoding="utf-8"))
MANIFEST = copy.deepcopy(SCHEMA["examples"][0])
MANIFEST["project_id"] = "hesabgar-man"
MANIFEST["repository"] = {
    "provider": "github", "repository_id": "1423683236",
    "full_name": "majidbusy09-blip/hesabgar_man",
    "url": "https://github.com/majidbusy09-blip/hesabgar_man",
    "default_branch": "main",
}
MANIFEST["lifecycle"] = "registered"
REPOSITORY = {
    "id": 1423683236, "full_name": "majidbusy09-blip/hesabgar_man",
    "html_url": "https://github.com/majidbusy09-blip/hesabgar_man",
    "default_branch": "main",
}
BINDING = {
    "project_id": "hesabgar-man", "repository_id": "1423683236",
    "repository_full_name": "majidbusy09-blip/hesabgar_man",
    "default_branch": "main", "manifest_schema_version": 1,
    "manifest_sha256": manifest_digest(MANIFEST),
}
TASK = {
    "schema_version": 2, "task_id": "sample-task",
    "goal": "Inspect a bounded project task and preserve it in the central inbox.",
    "capability": "investigation", "risk": "low", "assigned_agent": "any",
    "allow": ["docs/**"], "exclude": [],
    "scope_reason": "Read-only intake persistence test.",
    "verification_profiles": ["python-tooling-tests"], "project_binding": BINDING,
}


def artifact():
    return {
        "intake_schema": 2, "source": "github-issue",
        "repository": REPOSITORY["full_name"], "issue_number": 17,
        "issue_url": "https://github.com/majidbusy09-blip/hesabgar_man/issues/17",
        "issue_title": "Inbox persistence test", "issue_body_sha256": "a" * 64,
        "task": copy.deepcopy(TASK), "project_binding": BINDING,
        "project_lifecycle": "registered", "implementation_eligible": False,
        "execution": {
            "status": "validated-awaiting-activation", "lease_claimed": False,
            "agent_dispatched": False, "model_called": False, "source_uploaded": False,
        },
    }


class GitHubTaskInboxTests(unittest.TestCase):
    def ingest(self, root, value=None):
        raw = json.dumps(value or artifact(), ensure_ascii=False).encode("utf-8")
        return ingest_artifact_bytes(
            raw, root=root, repository_metadata=REPOSITORY,
            project_schema=SCHEMA, project_manifests=[MANIFEST],
        )

    def test_persists_project_scoped_durable_inbox_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = self.ingest(root)
            self.assertEqual(result["status"], "ingested")
            record = json.loads((root / result["path"]).read_text(encoding="utf-8"))
            self.assertEqual(record["queue_key"], "1423683236:17:sample-task")
            self.assertEqual(record["queue_status"], "awaiting_activation")
            self.assertFalse(record["intake_artifact"]["execution"]["lease_claimed"])

    def test_repeated_identical_artifact_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(self.ingest(root)["status"], "ingested")
            self.assertEqual(self.ingest(root)["status"], "already_ingested")

    def test_same_issue_with_changed_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.ingest(root)
            changed = artifact()
            changed["issue_body_sha256"] = "b" * 64
            with self.assertRaises(InboxError):
                self.ingest(root, changed)

    def test_rejects_repository_or_issue_url_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bad = artifact()
            bad["repository"] = "attacker/other"
            with self.assertRaises(InboxError):
                self.ingest(root, bad)
            bad = artifact()
            bad["issue_url"] = "https://github.com/attacker/other/issues/17"
            with self.assertRaises(InboxError):
                self.ingest(root, bad)

    def test_rejects_stale_manifest_binding_and_unsafe_execution_flags(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bad = artifact()
            bad["project_binding"] = dict(BINDING, manifest_sha256="b" * 64)
            with self.assertRaises(InboxError):
                self.ingest(root, bad)
            bad = artifact()
            bad["execution"]["lease_claimed"] = True
            with self.assertRaises(InboxError):
                self.ingest(root, bad)

    def test_rejects_active_status_claim_for_registered_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bad = artifact()
            bad["project_lifecycle"] = "active"
            bad["implementation_eligible"] = True
            bad["execution"]["status"] = "validated-awaiting-claim"
            with self.assertRaises(InboxError):
                self.ingest(root, bad)


if __name__ == "__main__":
    unittest.main()
