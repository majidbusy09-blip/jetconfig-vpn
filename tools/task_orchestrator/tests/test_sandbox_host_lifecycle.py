import unittest

from tools.task_orchestrator.sandbox_host_lifecycle import (
    CLEANED,
    EVIDENCE_ACCEPTED,
    EVIDENCE_REJECTED,
    FAILED,
    NEW,
    OBSERVING,
    RUNTIME_READY,
    TERMINATED,
    TERMINATING,
    HostLifecycleTracker,
    LifecycleContext,
    LifecycleError,
    LifecycleEvent,
)


ATTEMPT = "attempt-lifecycle-001"
RUNTIME = "runtime-fixture-001"
POLICY = "sha256:" + "c" * 64


def context(**changes):
    values = {
        "attempt_id": ATTEMPT,
        "runtime_id": RUNTIME,
        "policy_digest": POLICY,
        "started_monotonic_ns": 100,
        "deadline_monotonic_ns": 1000,
    }
    values.update(changes)
    return LifecycleContext(**values)


def event(event_type, at, **changes):
    values = {
        "event_type": event_type,
        "attempt_id": ATTEMPT,
        "runtime_id": RUNTIME,
        "policy_digest": POLICY,
        "monotonic_ns": at,
    }
    values.update(changes)
    return LifecycleEvent(**values)


class HostLifecycleTrackerTests(unittest.TestCase):
    def setUp(self):
        self.tracker = HostLifecycleTracker(context())

    def test_complete_success_path_requires_termination_and_cleanup(self):
        self.assertEqual(self.tracker.snapshot().state, NEW)
        self.tracker.advance(event("runtime_ready", 110))
        self.tracker.advance(event("observation_started", 120))
        accepted = self.tracker.advance(event("evidence_collected", 150, all_probes_pass=True))
        self.assertEqual(accepted.state, EVIDENCE_ACCEPTED)
        self.assertFalse(accepted.execution_authorized)
        self.assertFalse(accepted.eligible_for_untrusted_execution)
        self.tracker.advance(event("termination_requested", 160))
        self.assertEqual(self.tracker.snapshot().state, TERMINATING)
        self.tracker.advance(event("runtime_terminated", 170))
        self.assertEqual(self.tracker.snapshot().state, TERMINATED)
        cleaned = self.tracker.advance(event("cleanup_confirmed", 180))
        self.assertEqual(cleaned.state, CLEANED)
        self.assertEqual(cleaned.event_count, 6)
        self.assertFalse(cleaned.execution_authorized)

    def test_failed_evidence_cannot_enter_accepted_state(self):
        self.tracker.advance(event("runtime_ready", 110))
        self.tracker.advance(event("observation_started", 120))
        result = self.tracker.advance(event("evidence_collected", 130, all_probes_pass=False))
        self.assertEqual(result.state, EVIDENCE_REJECTED)
        self.tracker.advance(event("termination_requested", 140))
        self.tracker.advance(event("runtime_terminated", 150))
        self.assertEqual(self.tracker.advance(event("cleanup_confirmed", 160)).state, CLEANED)

    def test_cancel_and_deadline_paths_require_termination_and_cleanup(self):
        self.tracker.advance(event("runtime_ready", 110))
        self.tracker.advance(event("cancel_requested", 120))
        self.assertEqual(self.tracker.snapshot().state, TERMINATING)
        self.tracker.advance(event("runtime_terminated", 130))
        result = self.tracker.advance(event("cleanup_confirmed", 140))
        self.assertEqual(result.state, CLEANED)
        self.assertEqual(result.failure_code, "cancelled")

        timed = HostLifecycleTracker(context())
        timed.advance(event("runtime_ready", 110))
        result = timed.advance(event("deadline_expired", 1000))
        self.assertEqual(result.state, TERMINATING)
        self.assertEqual(result.failure_code, "deadline_exceeded")

    def test_adapter_failure_after_runtime_ready_still_requires_cleanup(self):
        self.tracker.advance(event("runtime_ready", 110))
        result = self.tracker.advance(event("adapter_failed", 120, failure_code="adapter_error"))
        self.assertEqual(result.state, TERMINATING)
        self.tracker.advance(event("runtime_terminated", 130))
        self.assertEqual(self.tracker.advance(event("cleanup_confirmed", 140)).state, CLEANED)

    def test_cleanup_failure_is_terminal_and_recorded(self):
        self.tracker.advance(event("runtime_ready", 110))
        self.tracker.advance(event("cancel_requested", 120))
        self.tracker.advance(event("runtime_terminated", 130))
        result = self.tracker.advance(event("cleanup_failed", 140, failure_code="cleanup_failed"))
        self.assertEqual(result.state, FAILED)
        self.assertEqual(result.failure_code, "cleanup_failed")
        with self.assertRaises(LifecycleError):
            self.tracker.advance(event("cleanup_confirmed", 150))

    def test_out_of_order_events_are_rejected_without_state_change(self):
        with self.assertRaisesRegex(LifecycleError, "invalid while state"):
            self.tracker.advance(event("observation_started", 110))
        self.assertEqual(self.tracker.snapshot().state, NEW)
        self.tracker.advance(event("runtime_ready", 120))
        with self.assertRaises(LifecycleError):
            self.tracker.advance(event("runtime_terminated", 130))
        self.assertEqual(self.tracker.snapshot().state, RUNTIME_READY)

    def test_attempt_runtime_and_policy_bindings_are_mandatory(self):
        for field, value in (
            ("attempt_id", "other-attempt"),
            ("runtime_id", "other-runtime"),
            ("policy_digest", "sha256:" + "d" * 64),
        ):
            with self.subTest(field=field):
                tracker = HostLifecycleTracker(context())
                with self.assertRaises(LifecycleError):
                    tracker.advance(event("runtime_ready", 110, **{field: value}))
                self.assertEqual(tracker.snapshot().state, NEW)

    def test_monotonic_order_and_deadline_are_enforced(self):
        self.tracker.advance(event("runtime_ready", 200))
        with self.assertRaisesRegex(LifecycleError, "moved backwards"):
            self.tracker.advance(event("observation_started", 199))
        with self.assertRaisesRegex(LifecycleError, "before the pinned deadline"):
            self.tracker.advance(event("deadline_expired", 999))
        with self.assertRaisesRegex(LifecycleError, "after deadline"):
            self.tracker.advance(event("observation_started", 1001))
        self.assertEqual(self.tracker.snapshot().state, RUNTIME_READY)
        self.assertEqual(
            self.tracker.advance(event("deadline_expired", 1000)).state,
            TERMINATING,
        )

    def test_event_payloads_and_failure_codes_are_allowlisted(self):
        with self.assertRaises(LifecycleError):
            self.tracker.advance(event("run-arbitrary-command", 110))
        with self.assertRaises(LifecycleError):
            self.tracker.advance(event("evidence_collected", 110, all_probes_pass="yes"))
        with self.assertRaises(LifecycleError):
            self.tracker.advance(event("adapter_failed", 110, failure_code="leak-secret-text"))

    def test_context_requires_pinned_deadline_and_policy_digest(self):
        with self.assertRaises(LifecycleError):
            HostLifecycleTracker(context(deadline_monotonic_ns=100))
        with self.assertRaises(LifecycleError):
            HostLifecycleTracker(context(policy_digest="not-a-digest"))


if __name__ == "__main__":
    unittest.main()
