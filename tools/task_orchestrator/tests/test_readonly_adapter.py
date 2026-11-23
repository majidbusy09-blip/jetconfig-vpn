import copy
import unittest

from tools.task_orchestrator.readonly_adapter import (
    FixtureReadOnlyProvider,
    ReadOnlyAdapterError,
    run_readonly,
)
from tools.task_orchestrator.tests.test_agent_contract import envelope, result_for


class ReadOnlyAdapterTests(unittest.TestCase):
    def test_valid_fixture_response_passes_contract_validation(self):
        env = envelope()
        provider = FixtureReadOnlyProvider(result_for(env))
        result = run_readonly(env, provider)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(provider.called)

    def test_provider_receives_deeply_immutable_envelope(self):
        env = envelope()

        testcase = self

        class MutatingProvider:
            def complete(self, supplied):
                with testcase.assertRaises(TypeError):
                    supplied["goal"] = "mutated"
                with testcase.assertRaises(TypeError):
                    supplied["repository"]["branch"] = "main"
                with testcase.assertRaises((AttributeError, TypeError)):
                    supplied["verification_profiles"].append("shell")
                return result_for(env)

        result = run_readonly(env, MutatingProvider())
        self.assertEqual(result["task_id"], env["task_id"])

    def test_rejects_invalid_envelope_before_provider_call(self):
        class NeverCall:
            called = False

            def complete(self, supplied):
                self.called = True
                return {}

        provider = NeverCall()
        env = envelope()
        env["scope"]["allowed_paths"] = ["../**"]
        with self.assertRaises(ReadOnlyAdapterError):
            run_readonly(env, provider)
        self.assertFalse(provider.called)

    def test_rejects_unstructured_or_invalid_provider_output(self):
        env = envelope()
        for bad_result in (None, [], {"status": "completed"}):
            class Provider:
                def complete(self, supplied):
                    return bad_result

            with self.subTest(bad_result=bad_result), self.assertRaises(ReadOnlyAdapterError):
                run_readonly(env, Provider())

    def test_rejects_provider_exceptions_without_leaking_exception_text(self):
        class BrokenProvider:
            def complete(self, supplied):
                raise RuntimeError("secret token should not be copied to diagnostics")

        with self.assertRaises(ReadOnlyAdapterError) as raised:
            run_readonly(envelope(), BrokenProvider())
        self.assertNotIn("secret token", str(raised.exception))

    def test_requires_explicit_complete_method(self):
        with self.assertRaises(ReadOnlyAdapterError):
            run_readonly(envelope(), object())

    def test_does_not_mutate_callers_envelope_or_result(self):
        env = envelope()
        original_env = copy.deepcopy(env)
        supplied_result = result_for(env)
        original_result = copy.deepcopy(supplied_result)
        run_readonly(env, FixtureReadOnlyProvider(supplied_result))
        self.assertEqual(env, original_env)
        self.assertEqual(supplied_result, original_result)


if __name__ == "__main__":
    unittest.main()
