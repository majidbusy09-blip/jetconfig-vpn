import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.github_lease import make_lease
from tools.task_orchestrator.github_lease_git import (
    LeaseGitError, _remote_url, _push, _commit_record, claim_or_renew,
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


    def test_project_lease_commit_uses_project_specific_ref_and_record_path(self):
        from tools.task_orchestrator.github_lease import lock_branch
        from tools.task_orchestrator.project_namespace import lease_record_path
        with tempfile.TemporaryDirectory(prefix="jet-project-lease-test-") as tmp:
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
            binding = {
                "project_id": "sample-flutter-app", "repository_id": "123456789",
                "repository_full_name": "owner/repo", "default_branch": "main",
                "manifest_schema_version": 1, "manifest_sha256": "a" * 64,
            }
            previous = Path.cwd()
            try:
                os.chdir(work)
                record = make_lease(
                    task_id="same-task", owner="chatgpt", claim_id="a" * 16,
                    base_sha=parent, now="2026-11-23T10:00:00Z",
                    project_binding=binding,
                )
                commit = _commit_record(parent, record, "test-token", binding)
                branch = lock_branch("same-task", binding)
                _push(str(bare), branch, commit, None, "test-token")
                path = lease_record_path("same-task", binding)
                loaded = subprocess.run(
                    ["git", "--git-dir", str(bare), "show", commit + ":" + path],
                    check=True, capture_output=True, text=True,
                ).stdout
                self.assertEqual(json.loads(loaded)["project_binding"], binding)
                self.assertEqual(json.loads(loaded)["schema_version"], 2)
            finally:
                os.chdir(previous)


    def test_renewal_reads_and_preserves_the_existing_pinned_base(self):
        from unittest.mock import patch
        current = make_lease(task_id="sample-task", owner="chatgpt",
                             claim_id="a" * 16, base_sha="c" * 40,
                             now="2026-11-23T10:00:00Z", duration_minutes=60)
        lock_sha = "d" * 40
        new_commit = "e" * 40
        with patch("tools.task_orchestrator.github_lease_git._remote_sha",
                   side_effect=[lock_sha, new_commit]), \
             patch("tools.task_orchestrator.github_lease_git._fetch_head",
                   return_value=lock_sha), \
             patch("tools.task_orchestrator.github_lease_git._read_lease",
                   return_value=current), \
             patch("tools.task_orchestrator.github_lease_git._commit_record",
                   return_value=new_commit), \
             patch("tools.task_orchestrator.github_lease_git._push") as push:
            result = claim_or_renew(
                operation="renew", task_id="sample-task", owner="chatgpt",
                claim_id="b" * 16, base_sha=None, duration_minutes=60,
                previous_claim_id="a" * 16, now="2026-11-23T10:30:00Z",
                repository="owner/repository", token="test-token",
            )
        self.assertEqual(result["base_sha"], "c" * 40)
        self.assertEqual(result["claim_id"], "b" * 16)
        self.assertEqual(result["expires_at"], "2026-11-23T11:30:00Z")
        self.assertEqual(push.call_args.args[3], lock_sha)


if __name__ == "__main__":
    unittest.main()
