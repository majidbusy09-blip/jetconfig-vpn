import unittest

from classify_ci_scope import requires_app_build


class ClassifyCiScopeTests(unittest.TestCase):
    def test_documentation_and_orchestrator_changes_skip_flutter_build(self):
        self.assertFalse(
            requires_app_build(
                [
                    "docs/CURRENT_STATUS.md",
                    "tools/task_orchestrator/sandbox_acceptance.py",
                    "tools/validation/test_prepare_validation_build.py",
                    "README.md",
                ]
            )
        )

    def test_application_source_and_tests_require_flutter_build(self):
        self.assertTrue(requires_app_build(["lib/main.dart"]))
        self.assertTrue(requires_app_build(["test/widget_test.dart"]))

    def test_android_and_root_gradle_files_require_build(self):
        self.assertTrue(requires_app_build(["android/app/build.gradle"]))
        self.assertTrue(requires_app_build(["settings.gradle"]))
        self.assertTrue(requires_app_build(["build.gradle.kts"]))

    def test_dependency_and_analyzer_configuration_require_build(self):
        self.assertTrue(requires_app_build(["pubspec.lock"]))
        self.assertTrue(requires_app_build(["analysis_options.yaml"]))

    def test_validation_apk_preparation_scripts_require_build(self):
        self.assertTrue(
            requires_app_build(["tools/validation/prepare_validation_build.py"])
        )
        self.assertTrue(
            requires_app_build(["tools/validation/align_validation_android.py"])
        )
        self.assertFalse(
            requires_app_build(["tools/validation/test_prepare_validation_build.py"])
        )

    def test_native_patch_and_validation_workflow_require_build(self):
        self.assertTrue(requires_app_build(["tools/v2ray_notif_patch/apply_patch.sh"]))
        self.assertTrue(
            requires_app_build([".github/workflows/pr-validation.yml"])
        )

    def test_empty_and_normalized_paths(self):
        self.assertFalse(requires_app_build(["", "docs/PLAN.md"]))
        self.assertTrue(requires_app_build([r"lib\\main.dart"]))


if __name__ == "__main__":
    unittest.main()
