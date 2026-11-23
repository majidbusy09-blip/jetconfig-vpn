import unittest
from tools.task_orchestrator.github_lease import LeaseError, make_lease, lock_branch, transition_plan, release_plan

BASE = "a" * 40
NOW = "2026-11-23T10:00:00Z"

def lease(owner="chatgpt", claim="a" * 16, minutes=60):
    return make_lease(task_id="sample-task", owner=owner, claim_id=claim, base_sha=BASE,
                      now=NOW, duration_minutes=minutes)

class GitHubLeaseTests(unittest.TestCase):
    def test_stable_lock_ref_and_safe_task_id(self):
        self.assertEqual(lock_branch("sample-task"), "agent-locks/sample-task")
        with self.assertRaises(LeaseError):
            lock_branch("../unsafe")

    def test_first_claim_requires_absent_ref(self):
        self.assertEqual(transition_plan(None, lease(), observed_ref_sha=None, now=NOW)["operation"], "create-lock-ref")
        with self.assertRaises(LeaseError):
            transition_plan(None, lease(), observed_ref_sha=BASE, now=NOW)

    def test_active_lease_cannot_be_stolen(self):
        with self.assertRaisesRegex(LeaseError, "already leased"):
            transition_plan(lease(), lease("grok", "b" * 16), observed_ref_sha=BASE, now=NOW)

    def test_expired_lease_requires_cas(self):
        plan = transition_plan(lease(minutes=1), lease("grok", "b" * 16), observed_ref_sha=BASE,
                               now="2026-11-23T10:02:00Z")
        self.assertEqual(plan["operation"], "compare-and-swap")
        self.assertEqual(plan["expected_sha"], BASE)

    def test_release_requires_matching_owner(self):
        plan = release_plan(lease(), observed_ref_sha=BASE, owner="chatgpt", claim_id="a" * 16, now=NOW)
        self.assertEqual(plan["record"]["status"], "released")
        with self.assertRaises(LeaseError):
            release_plan(lease(), observed_ref_sha=BASE, owner="grok", claim_id="a" * 16, now=NOW)

    def test_rejects_naive_time_and_long_duration(self):
        with self.assertRaises(LeaseError):
            make_lease(task_id="sample-task", owner="chatgpt", claim_id="a" * 16, base_sha=BASE,
                       now="2026-11-23T10:00:00", duration_minutes=60)
        with self.assertRaises(LeaseError):
            lease(minutes=241)

    def test_rejects_replayed_claim_and_bad_sha(self):
        with self.assertRaises(LeaseError):
            transition_plan(lease(), lease(), observed_ref_sha=BASE, now="2026-11-23T12:00:00Z")
        with self.assertRaises(LeaseError):
            make_lease(task_id="sample-task", owner="chatgpt", claim_id="a" * 16,
                       base_sha="bad", now=NOW)

if __name__ == "__main__":
    unittest.main()
