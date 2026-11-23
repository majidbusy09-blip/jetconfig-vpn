import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.github_lease import make_lease
from tools.task_orchestrator.github_lease_git import (
    LeaseGitError, _remote_url, _push, _commit_record,
)


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


    def test_git_object_commit_and_server_side_cas_against_local_bare_remote(self):
        with tempfile.TemporaryDirectory(prefix="jet-lease-test-") as tmp:
            root = Path(tmp)
            work = root / "work"
            bare = root / "remote.git"
            subprocess.run(["git", "init", "--bare", str(bare)], check=True,
                           capture_output=True, text=True)
            subprocess.run(["git", "init", str(work)], check=True,
                           capture_output=True, text=True)
            subprocess.run(["git", "config", "user.name", "Lease Test"], cwd=work,
                           check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "lease-test@example.invalid"],
                           cwd=work, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "base"], cwd=work,
                           check=True, capture_output=True, text=True)
            parent = subprocess.run(["git", "rev-parse", "HEAD"], cwd=work,
                                    check=True, capture_output=True, text=True).stdout.strip()
            previous = Path.cwd()
            try:
                os.chdir(work)
                first = make_lease(task_id="local-cas-test", owner="chatgpt",
                                   claim_id="a" * 16, base_sha=parent,
                                   now="2026-11-23T10:00:00Z", duration_minutes=60)
                first_commit = _commit_record(parent, first, "test-token")
                branch = "agent-locks/local-cas-test"
                _push(str(bare), branch, first_commit, None, "test-token")
                ref = "refs/heads/" + branch
                actual = subprocess.run(["git", "--git-dir", str(bare), "rev-parse", ref],
                                        check=True, capture_output=True, text=True).stdout.strip()
                self.assertEqual(actual, first_commit)
                self.assertEqual(json.loads(subprocess.run(
                    ["git", "show", first_commit + ":.agent-locks/lease.json"],
                    check=True, capture_output=True, text=True).stdout)["claim_id"], "a" * 16)

                renewed = make_lease(task_id="local-cas-test", owner="chatgpt",
                                     claim_id="b" * 16, base_sha=parent,
                                     now="2026-11-23T10:30:00Z", duration_minutes=60)
                second_commit = _commit_record(first_commit, renewed, "test-token")
                _push(str(bare), branch, second_commit, first_commit, "test-token")
                actual = subprocess.run(["git", "--git-dir", str(bare), "rev-parse", ref],
                                        check=True, capture_output=True, text=True).stdout.strip()
                self.assertEqual(actual, second_commit)

                stale_commit = _commit_record(first_commit, first, "test-token")
                with self.assertRaises(LeaseGitError):
                    _push(str(bare), branch, stale_commit, first_commit, "test-token")
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
