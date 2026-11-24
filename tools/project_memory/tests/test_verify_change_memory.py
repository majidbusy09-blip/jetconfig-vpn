import unittest

from tools.project_memory.verify_change_memory import (
    CORE_MEMORY,
    ARCHITECTURE_MEMORY,
    MEMORY_TOOLING_MEMORY,
    required_memory_paths,
    verify_memory_updates,
)


class ProjectMemoryChangeGateTests(unittest.TestCase):
    def test_documentation_only_change_does_not_require_memory_refresh(self):
        self.assertEqual(required_memory_paths(["docs/README.md"]), set())

    def test_application_change_requires_core_project_memory(self):
        required = required_memory_paths(["lib/main.dart", "test/widget_test.dart"])
        self.assertEqual(required, set(CORE_MEMORY))

    def test_task_orchestrator_change_requires_architecture_memory(self):
        required = required_memory_paths(["tools/task_orchestrator/task_orchestrator.py"])
        self.assertEqual(required, set(CORE_MEMORY) | set(ARCHITECTURE_MEMORY))

    def test_project_memory_tooling_change_requires_automation_memory(self):
        required = required_memory_paths(["tools/project_memory/index_dart.py"])
        self.assertEqual(
            required,
            set(CORE_MEMORY) | set(ARCHITECTURE_MEMORY) | set(MEMORY_TOOLING_MEMORY),
        )

    def test_workflow_change_requires_memory_automation_and_decisions(self):
        required = required_memory_paths([".github/workflows/project-memory-audit.yml"])
        self.assertEqual(
            required,
            set(CORE_MEMORY) | set(ARCHITECTURE_MEMORY) | set(MEMORY_TOOLING_MEMORY),
        )

    def test_missing_documents_are_reported(self):
        missing = verify_memory_updates(["tools/task_orchestrator/sandbox_trust.py"])
        self.assertEqual(missing, sorted(set(CORE_MEMORY) | set(ARCHITECTURE_MEMORY)))

    def test_complete_memory_update_passes(self):
        changed = [
            "tools/project_memory/verify_change_memory.py",
            *CORE_MEMORY,
            *ARCHITECTURE_MEMORY,
            *MEMORY_TOOLING_MEMORY,
        ]
        self.assertEqual(verify_memory_updates(changed), [])

    def test_package_and_native_app_changes_are_implementation_sensitive(self):
        self.assertEqual(required_memory_paths(["pubspec.lock"]), set(CORE_MEMORY))
        self.assertEqual(required_memory_paths(["android/app/src/main/AndroidManifest.xml"]), set(CORE_MEMORY))


if __name__ == "__main__":
    unittest.main()
