import unittest

from tools.task_orchestrator.project_namespace import (
    ProjectNamespaceError, lease_branch, lease_record_path, namespace_key, workspace_id,
)

BASE = "a" * 40
BINDING_A = {
    "project_id": "sample-flutter-app", "repository_id": "123456789",
    "repository_full_name": "owner/one", "default_branch": "main",
    "manifest_schema_version": 1, "manifest_sha256": "a" * 64,
}
BINDING_B = {
    "project_id": "second-flutter-app", "repository_id": "987654321",
    "repository_full_name": "owner/two", "default_branch": "main",
    "manifest_schema_version": 1, "manifest_sha256": "b" * 64,
}


class ProjectNamespaceTests(unittest.TestCase):
    def test_legacy_v1_namespace_is_preserved_exactly(self):
        self.assertEqual(lease_branch("same-task"), "agent-locks/same-task")
        self.assertEqual(lease_record_path("same-task"), ".agent-locks/lease.json")
        self.assertEqual(workspace_id("same-task", BASE),
                         "workspace_" + __import__("hashlib").sha256(
                             ("same-task:" + BASE).encode()).hexdigest()[:24])

    def test_same_task_id_is_isolated_by_project_and_repository_identity(self):
        self.assertNotEqual(lease_branch("same-task", BINDING_A),
                            lease_branch("same-task", BINDING_B))
        self.assertNotEqual(lease_record_path("same-task", BINDING_A),
                            lease_record_path("same-task", BINDING_B))
        self.assertNotEqual(workspace_id("same-task", BASE, BINDING_A),
                            workspace_id("same-task", BASE, BINDING_B))

    def test_namespace_stays_stable_on_repository_rename_but_binding_changes(self):
        renamed = dict(BINDING_A, repository_full_name="owner/renamed")
        self.assertEqual(namespace_key(BINDING_A), namespace_key(renamed))
        self.assertEqual(lease_branch("same-task", BINDING_A),
                         lease_branch("same-task", renamed))
        self.assertNotEqual(BINDING_A, renamed)

    def test_manifest_digest_change_changes_workspace_not_lock_namespace(self):
        changed = dict(BINDING_A, manifest_sha256="c" * 64)
        self.assertEqual(lease_branch("same-task", BINDING_A),
                         lease_branch("same-task", changed))
        self.assertNotEqual(workspace_id("same-task", BASE, BINDING_A),
                            workspace_id("same-task", BASE, changed))

    def test_rejects_malformed_or_unsafe_project_identity(self):
        for bad in (
            dict(BINDING_A, project_id="../escape"),
            dict(BINDING_A, repository_id="../123"),
            dict(BINDING_A, repository_full_name="https://evil.example/repo"),
            dict(BINDING_A, manifest_sha256="bad"),
            dict(BINDING_A, manifest_schema_version=True),
        ):
            with self.subTest(binding=bad), self.assertRaises(ProjectNamespaceError):
                lease_branch("same-task", bad)
        with self.assertRaises(ProjectNamespaceError):
            lease_branch("../unsafe", BINDING_A)


if __name__ == "__main__":
    unittest.main()
