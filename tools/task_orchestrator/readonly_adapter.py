"""Read-only coding-agent adapter boundary.

This prototype has no provider SDK, network client, filesystem access, command
runner, or patch application. A provider receives only a frozen task envelope
and returns data that is validated before it leaves this boundary.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Protocol

from tools.task_orchestrator.agent_contract import (
    ContractValidationError,
    validate_envelope,
    validate_result,
)


class ReadOnlyAdapterError(RuntimeError):
    """The read-only provider boundary failed closed."""


class ReadOnlyProvider(Protocol):
    """Minimal provider contract: one input object, one structured data result."""

    def complete(self, task_envelope: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return a structured result; no tools or workspace handles are supplied."""
        ...


def _freeze(value: Any) -> Any:
    """Defensively freeze nested JSON-like values before handing them to a provider."""
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def run_readonly(envelope: Mapping[str, Any], provider: ReadOnlyProvider) -> dict:
    """Validate, expose immutable bounded context, then validate provider output.

    This is an interface boundary, not an operating-system sandbox. The caller
    must only instantiate trusted provider implementations and must not pass
    filesystem, shell, GitHub, secret, or patch-writing capabilities to them.
    """
    if not isinstance(envelope, Mapping):
        raise ReadOnlyAdapterError("Task envelope must be a mapping.")
    canonical = copy.deepcopy(dict(envelope))
    try:
        validate_envelope(canonical)
    except ContractValidationError as exc:
        raise ReadOnlyAdapterError(f"Rejected task envelope: {exc}") from exc

    complete = getattr(provider, "complete", None)
    if not callable(complete):
        raise ReadOnlyAdapterError("Provider must expose a callable complete(envelope) method.")

    frozen_envelope = _freeze(canonical)
    try:
        raw_result = complete(frozen_envelope)
    except Exception as exc:
        raise ReadOnlyAdapterError(f"Read-only provider failed: {type(exc).__name__}") from exc

    if not isinstance(raw_result, Mapping):
        raise ReadOnlyAdapterError("Provider result must be a structured mapping.")
    result = copy.deepcopy(dict(raw_result))
    try:
        validate_result(result, canonical)
    except ContractValidationError as exc:
        raise ReadOnlyAdapterError(f"Rejected provider result: {exc}") from exc
    return result


class FixtureReadOnlyProvider:
    """Deterministic local fixture provider for adapter tests; no model/network."""

    def __init__(self, result: Mapping[str, Any]):
        self._result = copy.deepcopy(dict(result))
        self.called = False

    def complete(self, task_envelope: Mapping[str, Any]) -> Mapping[str, Any]:
        self.called = True
        return copy.deepcopy(self._result)
