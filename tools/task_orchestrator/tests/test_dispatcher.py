import copy
import unittest

from tools.task_orchestrator.dispatcher import (
    DispatcherError,
    dispatch_task,
    validate_dispatch_record,
)
from tools.task_orchestrator.readonly_adapter import FixtureReadOnlyProvider
from tools.task_orchestrator.tests.test_agent_contract import envelope, result_for


class DispatcherTests(unittest.TestCase):
    def test_dispatches_only_to_explicitly_registered_provider(self):
        env = envelope()
        result = result_for(env)
        provider = FixtureReadOnlyProvider(result)
        record = dispatch_task(env, provider_name="fixture", providers={"fixture": provider})
        self.assertEqual(record["status"], "completed")
        self.assertTrue(record["result_validated"])
        self.assertTrue(provider.called)
        self.assertFalse(record["patch_applied"])
        self.assertEqual(record["patch_validation"], "pending-artifact-validation")
        validate_dispatch_record(record)

    def test_rejects_unknown_provider_before_invocation(self):
        class NeverCall:
            called = False
            def complete(self, supplied):
                self.called = True
                return {}
        provider = NeverCall()
        with self.assertRaises(DispatcherError):
            dispatch_task(envelope(), provider_name="unregistered", providers={"fixture": provider})
        self.assertFalse(provider.called)

    def test_rejects_invalid_envelope_before_invocation(self):
        class NeverCall:
            called = False
            def complete(self, supplied):
                self.called = True
                return {}
        provider = NeverCall()
        env = envelope()
        env["scope"]["allowed_paths"] = ["../escape"]
        with self.assertRaises(DispatcherError):
            dispatch_task(env, provider_name="fixture", providers={"fixture": provider})
        self.assertFalse(provider.called)

    def test_rejects_result_provider_spoofing(self):
        env = envelope()
        supplied = result_for(env)
        supplied["provider"] = "other-provider"
        provider = FixtureReadOnlyProvider(supplied)
        with self.assertRaises(DispatcherError):
            dispatch_task(env, provider_name="fixture", providers={"fixture": provider})

    def test_audit_contains_no_source_text_or_raw_goal(self):
        env = envelope()
        record = dispatch_task(
            env, provider_name="fixture",
            providers={"fixture": FixtureReadOnlyProvider(result_for(env))},
        )
        serialized = str(record)
        self.assertNotIn(env["goal"], serialized)
        for item in env["source_context"]:
            self.assertNotIn(item["content"], serialized)

    def test_does_not_mutate_input_envelope(self):
        env = envelope()
        before = copy.deepcopy(env)
        dispatch_task(
            env, provider_name="fixture",
            providers={"fixture": FixtureReadOnlyProvider(result_for(env))},
        )
        self.assertEqual(env, before)

    def test_audit_rejects_claim_that_patch_was_applied(self):
        env = envelope()
        record = dispatch_task(
            env, provider_name="fixture",
            providers={"fixture": FixtureReadOnlyProvider(result_for(env))},
        )
        record["patch_applied"] = True
        with self.assertRaises(DispatcherError):
            validate_dispatch_record(record)


if __name__ == "__main__":
    unittest.main()
