import unittest
from tools.task_orchestrator.github_lease import (
    LeaseError, make_lease, lock_branch, transition_plan, release_plan, renew_plan,
)

BASE = "a" * 40
NOW = "2026-11-23T10:00:00Z"


def lease(owner="chatgpt", claim="a" * 16, minutes=60, now=NOW):
    return make_lease(task_id="sample-task", owner=owner, claim_id=claim,
                      base_sha=BASE, now=now, duration_minutes=minutes)


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

    def test_renewal_is_allowed_only_to_current_owner_before_expiry(self):
        proposed = lease(claim="b" * 16, minutes=60, now="2026-11-23T10:30:00Z")
        plan = renew_plan(lease(), proposed, observed_ref_sha=BASE, owner="chatgpt",
                          claim_id="a" * 16, now="2026-11-23T10:30:00Z")
        self.assertEqual(plan["operation"], "compare-and-swap")
        self.assertEqual(plan["record"]["claim_id"], "b" * 16)
        with self.assertRaises(LeaseError):
            renew_plan(lease(), proposed, observed_ref_sha=BASE, owner="grok",
                       claim_id="a" * 16, now="2026-11-23T10:30:00Z")

    def test_renewal_rejects_expired_or_replayed_claim(self):
        proposed = lease(claim="b" * 16, now="2026-11-23T10:30:00Z")
        with self.assertRaises(LeaseError):
            renew_plan(lease(minutes=10), proposed, observed_ref_sha=BASE, owner="chatgpt",
                       claim_id="a" * 16, now="2026-11-23T10:30:00Z")
        with self.assertRaises(LeaseError):
            renew_plan(lease(), lease(claim="a" * 16, now="2026-11-23T10:30:00Z"),
                       observed_ref_sha=BASE, owner="chatgpt", claim_id="a" * 16,
                       now="2026-11-23T10:30:00Z")


    def test_renewal_rejects_released_record_and_backdated_claim_time(self):
        released = dict(lease(claim="b" * 16, now="2026-11-23T10:30:00Z"), status="released")
        with self.assertRaises(LeaseError):
            renew_plan(lease(), released, observed_ref_sha=BASE, owner="chatgpt",
                       claim_id="a" * 16, now="2026-11-23T10:30:00Z")
        backdated = lease(claim="b" * 16, now="2026-11-23T09:59:00Z")
        with self.assertRaises(LeaseError):
            renew_plan(lease(), backdated, observed_ref_sha=BASE, owner="chatgpt",
                       claim_id="a" * 16, now="2026-11-23T09:59:00Z")

    def test_release_requires_matching_owner(self):
        plan = release_plan(lease(), observed_ref_sha=BASE, owner="chatgpt",
                            claim_id="a" * 16, now=NOW)
        self.assertEqual(plan["record"]["status"], "released")
        with self.assertRaises(LeaseError):
            release_plan(lease(), observed_ref_sha=BASE, owner="grok",
                         claim_id="a" * 16, now=NOW)

    def test_rejects_naive_time_and_long_duration(self):
        with self.assertRaises(LeaseError):
            make_lease(task_id="sample-task", owner="chatgpt", claim_id="a" * 16,
                       base_sha=BASE, now="2026-11-23T10:00:00", duration_minutes=60)
        with self.assertRaises(LeaseError):
            lease(minutes=241)

    def test_rejects_replayed_claim_bad_sha_and_base_change(self):
        with self.assertRaises(LeaseError):
            transition_plan(lease(), lease(), observed_ref_sha=BASE, now="2026-11-23T12:00:00Z")
        with self.assertRaises(LeaseError):
            make_lease(task_id="sample-task", owner="chatgpt", claim_id="a" * 16,
                       base_sha="bad", now=NOW)
        other_base = make_lease(task_id="sample-task", owner="grok", claim_id="b" * 16,
                                base_sha="b" * 40, now="2026-11-23T12:00:00Z")
        with self.assertRaises(LeaseError):
            transition_plan(lease(minutes=1), other_base, observed_ref_sha=BASE,
                            now="2026-11-23T12:00:00Z")

    def test_v2_project_lease_uses_namespace_and_rejects_cross_project_reuse(self):
        from tools.task_orchestrator.project_namespace import lease_record_path
        binding_a = {
            "project_id": "sample-flutter-app", "repository_id": "123456789",
            "repository_full_name": "owner/one", "default_branch": "main",
            "manifest_schema_version": 1, "manifest_sha256": "a" * 64,
        }
        binding_b = {
            "project_id": "second-flutter-app", "repository_id": "987654321",
            "repository_full_name": "owner/two", "default_branch": "main",
            "manifest_schema_version": 1, "manifest_sha256": "b" * 64,
        }
        first = make_lease(task_id="sample-task", owner="chatgpt", claim_id="a" * 16,
                           base_sha=BASE, now=NOW, project_binding=binding_a)
        self.assertEqual(first["schema_version"], 2)
        self.assertEqual(lock_branch("sample-task", binding_a),
                         "agent-locks/projects/sample-flutter-app/123456789/sample-task")
        self.assertEqual(lease_record_path("sample-task", binding_a),
                         ".agent-locks/projects/sample-flutter-app/123456789/sample-task.json")
        other = make_lease(task_id="sample-task", owner="grok", claim_id="b" * 16,
                           base_sha=BASE, now="2026-11-23T12:00:00Z", project_binding=binding_b)
        with self.assertRaisesRegex(LeaseError, "Project identity mismatch"):
            transition_plan(first, other, observed_ref_sha=BASE, now="2026-11-23T12:00:00Z")
        renewed_other = make_lease(task_id="sample-task", owner="chatgpt", claim_id="c" * 16,
                                   base_sha=BASE, now="2026-11-23T10:30:00Z",
                                   project_binding=binding_b)
        with self.assertRaisesRegex(LeaseError, "project identity"):
            renew_plan(first, renewed_other, observed_ref_sha=BASE, owner="chatgpt",
                       claim_id="a" * 16, now="2026-11-23T10:30:00Z")
        released = release_plan(first, observed_ref_sha=BASE, owner="chatgpt",
                                claim_id="a" * 16, now=NOW)
        self.assertEqual(released["branch"], lock_branch("sample-task", binding_a))

    def test_rejects_unhashable_lease_schema_owner_and_status_types(self):
        valid = make_lease(task_id="sample-task", owner="chatgpt", claim_id="a" * 16,
                           base_sha=BASE, now=NOW)
        for field, bad in (("schema_version", []), ("owner", []), ("status", {})):
            malformed = dict(valid)
            malformed[field] = bad
            with self.subTest(field=field), self.assertRaises(LeaseError):
                validate_lease(malformed)


if __name__ == "__main__":
    unittest.main()
