import hashlib
import unittest

from tools.task_orchestrator.sandbox_contract import (
    SandboxArtifact,
    SandboxCapabilities,
    SandboxContractError,
    SandboxExecution,
    SandboxLifecycle,
    SandboxLimits,
    SandboxRequest,
    SandboxSnapshot,
    SandboxState,
    run_synthetic_acceptance,
)


IMAGE = "sha256:" + "1" * 64
POLICY = "sha256:" + "2" * 64


def request(**overrides):
    values = {
        "task_id": "sandbox-test",
        "attempt_id": "attempt-001",
        "image_digest": IMAGE,
        "policy_digest": POLICY,
        "limits": SandboxLimits(
            cpu_millis=1000,
            memory_mib=512,
            process_count=32,
            disk_mib=512,
            wall_time_seconds=30,
        ),
    }
    values.update(overrides)
    return SandboxRequest(**values)


def good_capabilities():
    return SandboxCapabilities(
        runtime_class="linux_vm",
        ephemeral_vm=True,
        dedicated_kernel=True,
        pinned_image_digest=True,
        deny_all_egress_at_create=True,
        resource_limits_enforced=True,
        process_tree_termination=True,
        destroy_confirmation=True,
        credential_free_guest=True,
        bounded_artifact_export=True,
    )


class FakeSandboxProvider:
    def __init__(self, *, capabilities=None, egress="blocked", execution=None,
                 artifact=None, fail_destroy=False, fail_create=False):
        self.capabilities = capabilities or good_capabilities()
        self.egress = egress
        self.execution = execution or SandboxExecution(0, False, 0.25)
        content = b'{"result":"synthetic-ok"}'
        self.artifact = artifact or SandboxArtifact(
            "acceptance.json", content, hashlib.sha256(content).hexdigest()
        )
        self.fail_destroy = fail_destroy
        self.fail_create = fail_create
        self.state = SandboxState.NEW
        self.calls = []

    def create(self, request_value):
        self.calls.append("create")
        if self.fail_create:
            raise RuntimeError("provider detail must not escape")
        self.state = SandboxState.READY
        return "fake-sandbox-1"

    def inspect(self, sandbox_id):
        self.calls.append("inspect")
        return SandboxSnapshot(
            state=self.state,
            runtime_class="linux_vm",
            image_digest=IMAGE,
            egress_state=self.egress,
            dedicated_kernel=True,
            resource_limits_enforced=True,
            credentials_present=False,
            process_tree_termination=True,
        )

    def run_synthetic(self, sandbox_id, payload_id):
        self.calls.append(("run_synthetic", payload_id))
        self.state = SandboxState.RUNNING
        return self.execution

    def export_artifact(self, sandbox_id):
        self.calls.append("export_artifact")
        return self.artifact

    def terminate(self, sandbox_id):
        self.calls.append("terminate")
        self.state = SandboxState.TERMINATED

    def destroy(self, sandbox_id):
        self.calls.append("destroy")
        if self.fail_destroy:
            raise RuntimeError("destroy failed")
        self.state = SandboxState.DESTROYED


class SandboxContractTests(unittest.TestCase):
    def test_success_requires_verified_ready_state_and_confirmed_destruction(self):
        provider = FakeSandboxProvider()
        result = run_synthetic_acceptance(provider, request())
        self.assertEqual(result["status"], "synthetic_acceptance_passed")
        self.assertEqual(result["lifecycle"], [
            "new", "provisioning", "ready", "running",
            "stopping", "terminated", "destroyed",
        ])
        self.assertTrue(result["sandbox_destroyed"])
        self.assertFalse(result["patch_applied"])
        self.assertFalse(result["eligible_for_untrusted_execution"])
        self.assertEqual(provider.calls[-4:], ["terminate", "inspect", "destroy", "inspect"])

    def test_missing_capability_fails_before_sandbox_creation(self):
        caps = good_capabilities()
        caps = SandboxCapabilities(**{
            **caps.__dict__,
            "deny_all_egress_at_create": False,
        })
        provider = FakeSandboxProvider(capabilities=caps)
        with self.assertRaises(SandboxContractError):
            run_synthetic_acceptance(provider, request())
        self.assertNotIn("create", provider.calls)

    def test_open_egress_blocks_execution_but_still_cleans_up(self):
        provider = FakeSandboxProvider(egress="open")
        with self.assertRaises(SandboxContractError):
            run_synthetic_acceptance(provider, request())
        self.assertFalse(any(isinstance(call, tuple) and call[0] == "run_synthetic" for call in provider.calls))
        self.assertEqual(provider.calls[-3:], ["terminate", "inspect", "destroy"])

    def test_timeout_blocks_artifact_and_cleans_up(self):
        provider = FakeSandboxProvider(execution=SandboxExecution(124, True, 30))
        with self.assertRaises(SandboxContractError):
            run_synthetic_acceptance(provider, request())
        self.assertNotIn("export_artifact", provider.calls)
        self.assertEqual(provider.state, SandboxState.DESTROYED)


    def test_keyboard_interrupt_still_triggers_termination_and_destruction(self):
        class InterruptingProvider(FakeSandboxProvider):
            def run_synthetic(self, sandbox_id, payload_id):
                self.calls.append(("run_synthetic", payload_id))
                raise KeyboardInterrupt()

        provider = InterruptingProvider()
        with self.assertRaises(KeyboardInterrupt):
            run_synthetic_acceptance(provider, request())
        self.assertEqual(provider.state, SandboxState.DESTROYED)
        self.assertEqual(provider.calls[-4:], ["terminate", "inspect", "destroy", "inspect"])

    def test_artifact_digest_mismatch_blocks_and_cleans_up(self):
        provider = FakeSandboxProvider(artifact=SandboxArtifact(
            "acceptance.json", b'{"tampered":true}', "0" * 64
        ))
        with self.assertRaises(SandboxContractError):
            run_synthetic_acceptance(provider, request())
        self.assertEqual(provider.state, SandboxState.DESTROYED)

    def test_artifact_size_limit_blocks_and_cleans_up(self):
        raw = b"x" * (64 * 1024 + 1)
        provider = FakeSandboxProvider(artifact=SandboxArtifact(
            "acceptance.json", raw, hashlib.sha256(raw).hexdigest()
        ))
        with self.assertRaises(SandboxContractError):
            run_synthetic_acceptance(provider, request())
        self.assertEqual(provider.state, SandboxState.DESTROYED)

    def test_destroy_failure_is_a_hard_block(self):
        provider = FakeSandboxProvider(fail_destroy=True)
        with self.assertRaisesRegex(SandboxContractError, "cleanup could not be confirmed"):
            run_synthetic_acceptance(provider, request())
        self.assertNotEqual(provider.state, SandboxState.DESTROYED)

    def test_create_failure_does_not_leak_provider_error(self):
        provider = FakeSandboxProvider(fail_create=True)
        with self.assertRaisesRegex(SandboxContractError, "acceptance failed") as caught:
            run_synthetic_acceptance(provider, request())
        self.assertNotIn("provider detail", str(caught.exception))

    def test_request_rejects_network_allowlist_and_non_synthetic_payload(self):
        with self.assertRaises(SandboxContractError):
            run_synthetic_acceptance(FakeSandboxProvider(), request(network_policy="allow_github"))
        with self.assertRaises(SandboxContractError):
            run_synthetic_acceptance(FakeSandboxProvider(), request(payload_id="arbitrary-command"))

    def test_request_rejects_boolean_resource_limit(self):
        with self.assertRaises(SandboxContractError):
            run_synthetic_acceptance(
                FakeSandboxProvider(),
                request(limits=SandboxLimits(True, 512, 32, 512, 30)),
            )

    def test_lifecycle_rejects_skipped_transition_and_terminal_reuse(self):
        lifecycle = SandboxLifecycle()
        with self.assertRaises(SandboxContractError):
            lifecycle.transition(SandboxState.RUNNING)
        lifecycle.transition(SandboxState.PROVISIONING)
        lifecycle.transition(SandboxState.READY)
        lifecycle.transition(SandboxState.RUNNING)
        lifecycle.transition(SandboxState.STOPPING)
        lifecycle.transition(SandboxState.TERMINATED)
        lifecycle.transition(SandboxState.DESTROYED)
        with self.assertRaises(SandboxContractError):
            lifecycle.transition(SandboxState.PROVISIONING)


if __name__ == "__main__":
    unittest.main()
