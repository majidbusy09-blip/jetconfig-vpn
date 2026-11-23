import unittest

from tools.task_orchestrator.github_lease_git import LeaseGitError, _remote_url, _push


class GitHubLeaseTransportTests(unittest.TestCase):
    def test_remote_url_is_derived_from_valid_repository_identity(self):
        self.assertEqual(_remote_url("owner/repository"), "https://github.com/owner/repository.git")

    def test_remote_url_rejects_arbitrary_hosts_and_injection(self):
        for value in ("https://evil.example/owner/repo", "owner/repo\n--upload-pack=x",
                      "../repo", "owner/repo;echo"):
            with self.subTest(value=value), self.assertRaises(LeaseGitError):
                _remote_url(value)

    def test_cas_push_uses_server_side_force_with_lease(self):
        from unittest.mock import patch
        calls = []

        def fake_git(args, *, token, input_text=None, index_path=None):
            calls.append(args)
            if args[0] == "ls-remote":
                return "c" * 40 + "\trefs/heads/agent-locks/sample-task"
            return ""

        with patch("tools.task_orchestrator.github_lease_git._git", side_effect=fake_git):
            _push("https://github.com/owner/repo.git", "agent-locks/sample-task",
                  "c" * 40, "a" * 40, "token")
        self.assertIn("--force-with-lease=refs/heads/agent-locks/sample-task:" + "a" * 40,
                      calls[0])
        self.assertEqual(calls[0][0], "push")

    def test_initial_claim_uses_non_force_ref_creation(self):
        from unittest.mock import patch
        calls = []

        def fake_git(args, *, token, input_text=None, index_path=None):
            calls.append(args)
            if args[0] == "ls-remote":
                return "c" * 40 + "\trefs/heads/agent-locks/sample-task"
            return ""

        with patch("tools.task_orchestrator.github_lease_git._git", side_effect=fake_git):
            _push("https://github.com/owner/repo.git", "agent-locks/sample-task",
                  "c" * 40, None, "token")
        self.assertEqual(calls[0][0], "push")
        self.assertNotIn("--force", " ".join(calls[0]))


if __name__ == "__main__":
    unittest.main()
