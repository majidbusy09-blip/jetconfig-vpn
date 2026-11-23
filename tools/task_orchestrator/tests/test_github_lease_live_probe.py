import unittest

from tools.task_orchestrator.github_lease_live_probe import ProbeError, probe_branch


class GitHubLeaseLiveProbeTests(unittest.TestCase):
    def test_probe_branch_is_unique_and_scoped(self):
        self.assertEqual(probe_branch("45123456789", "1"),
                         "agent-locks/ci-cas-probe-45123456789-1")

    def test_probe_branch_rejects_untrusted_run_identity(self):
        for run_id, attempt in (("../evil", "1"), ("12", "../../"), ("", "1")):
            with self.subTest(run_id=run_id, attempt=attempt), self.assertRaises(ProbeError):
                probe_branch(run_id, attempt)


if __name__ == "__main__":
    unittest.main()
