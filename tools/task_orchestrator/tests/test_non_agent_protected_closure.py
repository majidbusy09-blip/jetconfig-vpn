import unittest
from unittest.mock import patch

from tools.task_orchestrator.github_task_pr_guard import (
    GuardError,
    validate_non_agent_pr,
)

REPOSITORY = "majidbusy09-blip/jetconfig-vpn"
REPOSITORY_METADATA = {
    "id": 1349356614,
    "full_name": REPOSITORY,
    "html_url": "https://github.com/" + REPOSITORY,
    "default_branch": "main",
}


def ordinary_event():
    return {
        "action": "opened",
        "repository": dict(REPOSITORY_METADATA),
        "pull_request": {
            "state": "open",
            "number": 7,
            "base": {
                "ref": "main",
                "repo": dict(REPOSITORY_METADATA),
            },
        },
    }


def api_for(files):
    def fake_api(repository, path, token):
        if path == "":
            return dict(REPOSITORY_METADATA)
        if path.startswith("/pulls/7/files?"):
            return files
        raise AssertionError("Unexpected API path: " + path)
    return fake_api


class NonAgentProtectedClosureTests(unittest.TestCase):
    def assert_rejected(self, item):
        with patch(
            "tools.task_orchestrator.github_task_pr_guard.api_get",
            side_effect=api_for([item]),
        ), self.assertRaises(GuardError):
            validate_non_agent_pr(
                ordinary_event(), token="read-token", repository=REPOSITORY
            )

    def test_rejects_ci_classifier_and_transitive_tooling(self):
        protected = (
            "tools/validation/classify_ci_scope.py",
            "tools/project_memory/index_dart.py",
            "tools/v2ray_notif_patch/apply_patch.sh",
            "tools/task_orchestrator/dispatcher.py",
            "tools/other/future_ci_helper.py",
        )
        for filename in protected:
            with self.subTest(filename=filename):
                self.assert_rejected({"filename": filename, "status": "modified"})

    def test_rejects_all_github_policy_paths(self):
        for filename in (
            ".github/workflows/release.yml",
            ".github/actions/security/action.yml",
            ".github/dependabot.yml",
            ".github",
        ):
            with self.subTest(filename=filename):
                self.assert_rejected({"filename": filename, "status": "added"})

    def test_rejects_codeowners_in_all_supported_locations(self):
        for filename in ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"):
            with self.subTest(filename=filename):
                self.assert_rejected({"filename": filename, "status": "added"})

    def test_rejects_build_and_dependency_control_files(self):
        for filename in (
            "android/app/build.gradle",
            "android/settings.gradle",
            "android/gradlew",
            "android/gradle/wrapper/gradle-wrapper.properties",
            "android/app/proguard-rules.pro",
            "analysis_options.yaml",
            "gradlew",
            "pubspec.yaml",
            "pubspec.lock",
        ):
            with self.subTest(filename=filename):
                self.assert_rejected({"filename": filename, "status": "modified"})

    def test_rejects_rename_out_of_protected_tree(self):
        self.assert_rejected({
            "filename": "docs/classifier.txt",
            "previous_filename": "tools/validation/classify_ci_scope.py",
            "status": "renamed",
        })

    def test_allows_ordinary_application_and_documentation_changes(self):
        files = [
            {"filename": "lib/main.dart", "status": "modified"},
            {"filename": "docs/guide.md", "status": "modified"},
        ]
        with patch(
            "tools.task_orchestrator.github_task_pr_guard.api_get",
            side_effect=api_for(files),
        ):
            result = validate_non_agent_pr(
                ordinary_event(), token="read-token", repository=REPOSITORY
            )
        self.assertEqual(result["status"], "not-agent-pr")
        self.assertEqual(
            result["changed_paths"], ["lib/main.dart", "docs/guide.md"]
        )

    def test_rejects_unsafe_and_unknown_file_metadata(self):
        for item in (
            {"filename": "../escape.py", "status": "modified"},
            {"filename": "docs/guide.md", "status": "copied"},
            {"status": "modified"},
        ):
            with self.subTest(item=item):
                self.assert_rejected(item)


if __name__ == "__main__":
    unittest.main()
