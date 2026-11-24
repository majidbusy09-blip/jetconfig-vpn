"""Provider-neutral fail-closed sandbox lifecycle contract.

This module supports only a fixed synthetic acceptance payload. It does not
launch processes, upload source, connect a provider, or execute model output.
A real adapter must be separately reviewed and runtime-acceptance tested.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


MAX_ACCEPTANCE_ARTIFACT_BYTES = 64 * 1024
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SYNTHETIC_PAYLOAD_ID = "synthetic-acceptance-v1"

REQUIRED_CAPABILITIES = (
    "ephemeral_vm",
    "dedicated_kernel",
    "pinned_image_digest",
    "deny_all_egress_at_create",
    "resource_limits_enforced",
    "process_tree_termination",
    "destroy_confirmation",
    "credential_free_guest",
    "bounded_artifact_export",
)


class SandboxContractError(ValueError):
    """A sandbox request, runtime observation, or lifecycle failed closed."""


class SandboxState(str, Enum):
    NEW = "new"
    PROVISIONING = "provisioning"
    READY = "ready"
    RUNNING = "running"
    FAILED = "failed"
    STOPPING = "stopping"
    TERMINATED = "terminated"
    DESTROYED = "destroyed"


_ALLOWED_TRANSITIONS = {
    SandboxState.NEW: {SandboxState.PROVISIONING, SandboxState.FAILED},
    SandboxState.PROVISIONING: {SandboxState.READY, SandboxState.FAILED, SandboxState.STOPPING},
    SandboxState.READY: {SandboxState.RUNNING, SandboxState.FAILED, SandboxState.STOPPING},
    SandboxState.RUNNING: {SandboxState.FAILED, SandboxState.STOPPING},
    SandboxState.FAILED: {SandboxState.STOPPING},
    SandboxState.STOPPING: {SandboxState.TERMINATED, SandboxState.FAILED},
    SandboxState.TERMINATED: {SandboxState.DESTROYED, SandboxState.FAILED},
    SandboxState.DESTROYED: set(),
}


@dataclass(frozen=True)
class SandboxLimits:
    cpu_millis: int
    memory_mib: int
    process_count: int
    disk_mib: int
    wall_time_seconds: int

    def validate(self) -> None:
        bounds = {
            "cpu_millis": (100, 8000),
            "memory_mib": (128, 8192),
            "process_count": (1, 512),
            "disk_mib": (64, 4096),
            "wall_time_seconds": (1, 900),
        }
        for name, (minimum, maximum) in bounds.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
                raise SandboxContractError(f"Sandbox limit {name} is outside its allowed range.")


@dataclass(frozen=True)
class SandboxRequest:
    task_id: str
    attempt_id: str
    image_digest: str
    policy_digest: str
    limits: SandboxLimits
    network_policy: str = "deny_all"
    payload_id: str = SYNTHETIC_PAYLOAD_ID

    def validate(self) -> None:
        if not isinstance(self.task_id, str) or not _TASK_ID_RE.fullmatch(self.task_id):
            raise SandboxContractError("Task ID is invalid.")
        if not isinstance(self.attempt_id, str) or not _TASK_ID_RE.fullmatch(self.attempt_id):
            raise SandboxContractError("Attempt ID is invalid.")
        if not isinstance(self.image_digest, str) or not _SHA256_RE.fullmatch(self.image_digest):
            raise SandboxContractError("A pinned SHA-256 image digest is required.")
        if not isinstance(self.policy_digest, str) or not _SHA256_RE.fullmatch(self.policy_digest):
            raise SandboxContractError("A pinned SHA-256 policy digest is required.")
        if self.network_policy != "deny_all":
            raise SandboxContractError("Only deny-all network policy is supported.")
        if self.payload_id != SYNTHETIC_PAYLOAD_ID:
            raise SandboxContractError("Only the fixed synthetic acceptance payload is supported.")
        if not isinstance(self.limits, SandboxLimits):
            raise SandboxContractError("Explicit sandbox resource limits are required.")
        self.limits.validate()


@dataclass(frozen=True)
class SandboxCapabilities:
    runtime_class: str
    ephemeral_vm: bool
    dedicated_kernel: bool
    pinned_image_digest: bool
    deny_all_egress_at_create: bool
    resource_limits_enforced: bool
    process_tree_termination: bool
    destroy_confirmation: bool
    credential_free_guest: bool
    bounded_artifact_export: bool


def validate_capabilities(capabilities: SandboxCapabilities) -> None:
    """Check declared capabilities; this is not runtime proof or authorization."""
    if not isinstance(capabilities, SandboxCapabilities):
        raise SandboxContractError("Provider capability declaration is missing or malformed.")
    if capabilities.runtime_class != "linux_vm":
        raise SandboxContractError("Only a dedicated Linux VM runtime is eligible.")
    missing = [
        name for name in REQUIRED_CAPABILITIES
        if getattr(capabilities, name) is not True
    ]
    if missing:
        raise SandboxContractError("Provider is missing required capabilities: " + ", ".join(missing))


@dataclass(frozen=True)
class SandboxSnapshot:
    state: SandboxState
    runtime_class: str
    image_digest: str
    egress_state: str
    dedicated_kernel: bool
    resource_limits_enforced: bool
    credentials_present: bool
    process_tree_termination: bool


@dataclass(frozen=True)
class SandboxExecution:
    exit_code: int
    timed_out: bool
    duration_seconds: float


@dataclass(frozen=True)
class SandboxArtifact:
    name: str
    content: bytes
    sha256: str


class SandboxProvider(Protocol):
    """Narrow provider API: no arbitrary shell, source upload, or credentials."""

    @property
    def capabilities(self) -> SandboxCapabilities: ...

    def create(self, request: SandboxRequest) -> str: ...
    def inspect(self, sandbox_id: str) -> SandboxSnapshot: ...
    def run_synthetic(self, sandbox_id: str, payload_id: str) -> SandboxExecution: ...
    def export_artifact(self, sandbox_id: str) -> SandboxArtifact: ...
    def terminate(self, sandbox_id: str) -> None: ...
    def destroy(self, sandbox_id: str) -> None: ...


class SandboxLifecycle:
    """Small auditable state machine; invalid or repeated transitions fail."""

    def __init__(self) -> None:
        self.state = SandboxState.NEW
        self.history = [self.state.value]

    def transition(self, next_state: SandboxState) -> None:
        if not isinstance(next_state, SandboxState) or next_state not in _ALLOWED_TRANSITIONS[self.state]:
            raise SandboxContractError(
                f"Invalid sandbox lifecycle transition: {self.state.value} -> {getattr(next_state, 'value', 'unknown')}."
            )
        self.state = next_state
        self.history.append(next_state.value)


def _validate_ready_snapshot(snapshot: SandboxSnapshot, request: SandboxRequest) -> None:
    if not isinstance(snapshot, SandboxSnapshot) or snapshot.state is not SandboxState.READY:
        raise SandboxContractError("Sandbox did not reach a verified ready state.")
    if snapshot.runtime_class != "linux_vm" or snapshot.image_digest != request.image_digest:
        raise SandboxContractError("Sandbox runtime class or pinned image digest does not match.")
    if snapshot.egress_state != "blocked":
        raise SandboxContractError("Sandbox deny-all egress was not observed.")
    if snapshot.dedicated_kernel is not True:
        raise SandboxContractError("A dedicated guest kernel was not observed.")
    if snapshot.resource_limits_enforced is not True:
        raise SandboxContractError("Sandbox resource limits were not observed as enforced.")
    if snapshot.credentials_present is not False:
        raise SandboxContractError("Sandbox guest must not contain credentials.")
    if snapshot.process_tree_termination is not True:
        raise SandboxContractError("Process-tree termination capability was not observed.")


def _validate_artifact(artifact: SandboxArtifact) -> dict:
    if not isinstance(artifact, SandboxArtifact) or artifact.name != "acceptance.json":
        raise SandboxContractError("Only the fixed acceptance artifact may be exported.")
    if not isinstance(artifact.content, bytes) or not artifact.content:
        raise SandboxContractError("Acceptance artifact must be non-empty bytes.")
    if len(artifact.content) > MAX_ACCEPTANCE_ARTIFACT_BYTES:
        raise SandboxContractError("Acceptance artifact exceeds the size limit.")
    digest = hashlib.sha256(artifact.content).hexdigest()
    if artifact.sha256 != digest:
        raise SandboxContractError("Acceptance artifact digest does not match its exact bytes.")
    return {"name": artifact.name, "bytes": len(artifact.content), "sha256": digest}


def run_synthetic_acceptance(provider: SandboxProvider, request: SandboxRequest) -> dict:
    """Run one fixed benign acceptance payload and require confirmed destruction.

    Provider declarations alone are insufficient: the ready-state observation
    is checked independently by the caller. Only a trusted control plane should
    call this function after reviewing actual runtime acceptance evidence.
    """
    request.validate()
    validate_capabilities(getattr(provider, "capabilities", None))

    lifecycle = SandboxLifecycle()
    sandbox_id = None
    artifact_record = None
    primary_error = None
    cleanup_error = None

    try:
        lifecycle.transition(SandboxState.PROVISIONING)
        sandbox_id = provider.create(request)
        if not isinstance(sandbox_id, str) or not sandbox_id or len(sandbox_id) > 256:
            raise SandboxContractError("Provider returned an invalid sandbox handle.")
        lifecycle.transition(SandboxState.READY)
        _validate_ready_snapshot(provider.inspect(sandbox_id), request)

        lifecycle.transition(SandboxState.RUNNING)
        execution = provider.run_synthetic(sandbox_id, request.payload_id)
        if not isinstance(execution, SandboxExecution):
            raise SandboxContractError("Provider returned an invalid execution record.")
        if isinstance(execution.exit_code, bool) or not isinstance(execution.exit_code, int):
            raise SandboxContractError("Synthetic acceptance exit code is invalid.")
        if type(execution.timed_out) is not bool:
            raise SandboxContractError("Synthetic acceptance timeout flag is invalid.")
        if (
            isinstance(execution.duration_seconds, bool)
            or not isinstance(execution.duration_seconds, (int, float))
            or execution.duration_seconds < 0
            or execution.duration_seconds > request.limits.wall_time_seconds
        ):
            raise SandboxContractError("Synthetic acceptance exceeded its wall-clock budget.")
        if execution.timed_out or execution.exit_code != 0:
            raise SandboxContractError("Synthetic acceptance payload did not pass.")
        artifact_record = _validate_artifact(provider.export_artifact(sandbox_id))
    except Exception as exc:  # provider exceptions are deliberately sanitized
        primary_error = exc
        if lifecycle.state not in {SandboxState.FAILED, SandboxState.DESTROYED}:
            lifecycle.transition(SandboxState.FAILED)

    if sandbox_id is not None:
        try:
            if lifecycle.state is not SandboxState.STOPPING:
                lifecycle.transition(SandboxState.STOPPING)
            provider.terminate(sandbox_id)
            terminated = provider.inspect(sandbox_id)
            if not isinstance(terminated, SandboxSnapshot) or terminated.state is not SandboxState.TERMINATED:
                raise SandboxContractError("Provider did not confirm sandbox termination.")
            lifecycle.transition(SandboxState.TERMINATED)
            provider.destroy(sandbox_id)
            destroyed = provider.inspect(sandbox_id)
            if not isinstance(destroyed, SandboxSnapshot) or destroyed.state is not SandboxState.DESTROYED:
                raise SandboxContractError("Provider did not confirm sandbox destruction.")
            lifecycle.transition(SandboxState.DESTROYED)
        except Exception as exc:
            cleanup_error = exc
            if lifecycle.state not in {SandboxState.FAILED, SandboxState.DESTROYED}:
                lifecycle.transition(SandboxState.FAILED)
    elif primary_error is None:
        primary_error = SandboxContractError("Provider did not return a sandbox handle.")

    if cleanup_error is not None:
        raise SandboxContractError(
            "Sandbox cleanup could not be confirmed; the attempt is blocked."
        ) from cleanup_error
    if primary_error is not None:
        raise SandboxContractError(
            "Sandbox acceptance failed; no artifact is eligible for review."
        ) from primary_error
    if lifecycle.state is not SandboxState.DESTROYED:
        raise SandboxContractError("Sandbox did not reach the destroyed terminal state.")

    return {
        "schema_version": 1,
        "status": "synthetic_acceptance_passed",
        "task_id": request.task_id,
        "attempt_id": request.attempt_id,
        "runtime_class": "linux_vm",
        "image_digest": request.image_digest,
        "policy_digest": request.policy_digest,
        "lifecycle": list(lifecycle.history),
        "sandbox_destroyed": True,
        "artifact": artifact_record,
        "patch_applied": False,
    }
