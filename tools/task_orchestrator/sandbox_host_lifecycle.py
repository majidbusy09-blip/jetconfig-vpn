"""Pure fail-closed lifecycle state machine for a future Sandbox host controller.

This module validates event ordering only. It performs no I/O and cannot launch,
inspect, terminate, or clean up a runtime.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

NEW = "new"
RUNTIME_READY = "runtime_ready"
OBSERVING = "observing"
EVIDENCE_ACCEPTED = "evidence_accepted"
EVIDENCE_REJECTED = "evidence_rejected"
TERMINATING = "terminating"
TERMINATED = "terminated"
CLEANED = "cleaned"
FAILED = "failed"

_ALLOWED_EVENTS = frozenset({
    "runtime_ready",
    "observation_started",
    "evidence_collected",
    "termination_requested",
    "cancel_requested",
    "deadline_expired",
    "adapter_failed",
    "runtime_terminated",
    "cleanup_confirmed",
    "cleanup_failed",
})
_FAILURE_CODES = frozenset({"adapter_error", "cancelled", "deadline_exceeded", "cleanup_failed"})


class LifecycleError(ValueError):
    """A lifecycle event is malformed, stale, out of order, or out of scope."""


@dataclass(frozen=True)
class LifecycleContext:
    attempt_id: str
    runtime_id: str
    policy_digest: str
    started_monotonic_ns: int
    deadline_monotonic_ns: int

    def validate(self) -> None:
        for field in ("attempt_id", "runtime_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not _ID_RE.fullmatch(value):
                raise LifecycleError(f"Lifecycle {field} is invalid.")
        if not isinstance(self.policy_digest, str) or not _SHA256_RE.fullmatch(self.policy_digest):
            raise LifecycleError("Lifecycle policy digest must be a lowercase SHA-256 digest.")
        for field in ("started_monotonic_ns", "deadline_monotonic_ns"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise LifecycleError(f"Lifecycle {field} must be a non-negative integer.")
        if self.deadline_monotonic_ns <= self.started_monotonic_ns:
            raise LifecycleError("Lifecycle deadline must be after its start.")


@dataclass(frozen=True)
class LifecycleEvent:
    event_type: str
    attempt_id: str
    runtime_id: str
    policy_digest: str
    monotonic_ns: int
    all_probes_pass: bool | None = None
    failure_code: str | None = None


@dataclass(frozen=True)
class LifecycleSnapshot:
    state: str
    last_monotonic_ns: int
    event_count: int
    failure_code: str | None
    history: tuple[str, ...]
    execution_authorized: bool = False
    eligible_for_untrusted_execution: bool = False


_TRANSITIONS: Mapping[str, Mapping[str, str]] = MappingProxyType({
    NEW: MappingProxyType({"runtime_ready": RUNTIME_READY, "adapter_failed": FAILED}),
    RUNTIME_READY: MappingProxyType({
        "observation_started": OBSERVING,
        "cancel_requested": TERMINATING,
        "deadline_expired": TERMINATING,
        "adapter_failed": TERMINATING,
    }),
    OBSERVING: MappingProxyType({
        "evidence_collected": EVIDENCE_ACCEPTED,
        "cancel_requested": TERMINATING,
        "deadline_expired": TERMINATING,
        "adapter_failed": TERMINATING,
    }),
    EVIDENCE_ACCEPTED: MappingProxyType({
        "termination_requested": TERMINATING,
        "cancel_requested": TERMINATING,
        "deadline_expired": TERMINATING,
        "adapter_failed": TERMINATING,
    }),
    EVIDENCE_REJECTED: MappingProxyType({
        "termination_requested": TERMINATING,
        "cancel_requested": TERMINATING,
        "deadline_expired": TERMINATING,
        "adapter_failed": TERMINATING,
    }),
    TERMINATING: MappingProxyType({"runtime_terminated": TERMINATED}),
    TERMINATED: MappingProxyType({
        "cleanup_confirmed": CLEANED,
        "cleanup_failed": FAILED,
    }),
    CLEANED: MappingProxyType({}),
    FAILED: MappingProxyType({}),
})


class HostLifecycleTracker:
    """Validate a fixed lifecycle event stream without invoking an adapter."""

    def __init__(self, context: LifecycleContext) -> None:
        if not isinstance(context, LifecycleContext):
            raise LifecycleError("A typed pinned lifecycle context is required.")
        context.validate()
        self._context = context
        self._state = NEW
        self._last_monotonic_ns = context.started_monotonic_ns
        self._history: list[str] = []
        self._failure_code: str | None = None

    def snapshot(self) -> LifecycleSnapshot:
        return LifecycleSnapshot(
            state=self._state,
            last_monotonic_ns=self._last_monotonic_ns,
            event_count=len(self._history),
            failure_code=self._failure_code,
            history=tuple(self._history),
        )

    def advance(self, event: LifecycleEvent) -> LifecycleSnapshot:
        if not isinstance(event, LifecycleEvent):
            raise LifecycleError("Lifecycle events must use the typed event contract.")
        if event.event_type not in _ALLOWED_EVENTS:
            raise LifecycleError("Lifecycle event type is not allowlisted.")
        if event.attempt_id != self._context.attempt_id:
            raise LifecycleError("Lifecycle event attempt identity mismatch.")
        if event.runtime_id != self._context.runtime_id:
            raise LifecycleError("Lifecycle event runtime identity mismatch.")
        if event.policy_digest != self._context.policy_digest:
            raise LifecycleError("Lifecycle event policy digest mismatch.")
        if isinstance(event.monotonic_ns, bool) or not isinstance(event.monotonic_ns, int):
            raise LifecycleError("Lifecycle event time must be an integer monotonic offset.")
        if event.monotonic_ns < self._last_monotonic_ns:
            raise LifecycleError("Lifecycle event time moved backwards.")
        if event.monotonic_ns < self._context.started_monotonic_ns:
            raise LifecycleError("Lifecycle event predates the pinned start.")
        if event.event_type == "deadline_expired":
            if event.monotonic_ns < self._context.deadline_monotonic_ns:
                raise LifecycleError("Deadline-expired event occurred before the pinned deadline.")
        elif self._state not in {TERMINATING, TERMINATED} and event.monotonic_ns > self._context.deadline_monotonic_ns:
            raise LifecycleError("An active lifecycle event arrived after deadline without timeout transition.")

        if event.event_type == "evidence_collected":
            if type(event.all_probes_pass) is not bool or event.failure_code is not None:
                raise LifecycleError("Evidence event must carry exactly one boolean aggregate outcome.")
        elif event.all_probes_pass is not None:
            raise LifecycleError("Only evidence_collected may carry a probe outcome.")

        if event.event_type in {"adapter_failed", "cleanup_failed"}:
            if event.failure_code not in _FAILURE_CODES:
                raise LifecycleError("Failure event requires an allowlisted failure code.")
        elif event.failure_code is not None:
            raise LifecycleError("Unexpected failure code on a non-failure event.")

        next_state = _TRANSITIONS[self._state].get(event.event_type)
        if next_state is None:
            raise LifecycleError(f"Event {event.event_type} is invalid while state is {self._state}.")

        if event.event_type == "evidence_collected" and event.all_probes_pass is False:
            next_state = EVIDENCE_REJECTED
        if event.event_type == "cancel_requested":
            self._failure_code = "cancelled"
        elif event.event_type == "deadline_expired":
            self._failure_code = "deadline_exceeded"
        elif event.event_type == "adapter_failed":
            self._failure_code = event.failure_code
        elif event.event_type == "cleanup_failed":
            self._failure_code = "cleanup_failed"

        self._state = next_state
        self._last_monotonic_ns = event.monotonic_ns
        self._history.append(event.event_type)
        return self.snapshot()
