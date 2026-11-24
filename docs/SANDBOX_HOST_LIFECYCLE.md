# Host Controller Lifecycle Contract

**Status:** pure state-transition validator with deterministic unit tests. It does not operate a runtime.

## Scope

`sandbox_host_lifecycle.py` validates a fixed lifecycle event stream for a future trusted host controller. It has no subprocess, shell, filesystem, socket, network, provider, VM, guest, or credential capability. No adapter is invoked by this module.

## Pinned context

Each tracker is created with:
- one attempt ID;
- one pre-pinned runtime ID;
- one SHA-256 policy digest;
- a host monotonic start offset and deadline.

Every event must match the same attempt/runtime/policy tuple and carry a nondecreasing monotonic offset. A deadline-expired event cannot be accepted before the pinned deadline. Active events after the deadline are rejected unless the explicit timeout transition is recorded.

## State machine

```text
NEW
  -> RUNTIME_READY
  -> OBSERVING
  -> EVIDENCE_ACCEPTED | EVIDENCE_REJECTED
  -> TERMINATING
  -> TERMINATED
  -> CLEANED

RUNTIME_READY / OBSERVING / EVIDENCE_* 
  -> TERMINATING on cancel, deadline, or adapter failure
TERMINATED
  -> FAILED on cleanup failure
NEW
  -> FAILED on adapter failure before runtime readiness
```

- Evidence is accepted only as a boolean aggregate event from the caller; this state machine does not validate probe semantics or signatures.
- Both accepted and rejected evidence paths must explicitly request termination, confirm runtime termination, and confirm cleanup.
- Cancellation, deadline expiry, and adapter failure require termination and cleanup when a runtime may exist.
- Cleanup failure is terminal and recorded as failure.
- Terminal states reject further events.

## Failure and security semantics

- Event names and failure codes are allowlisted; no shell command, arbitrary callback, error text, or task-supplied action is accepted.
- Event identity mismatches, backward monotonic time, invalid transitions, and invalid deadline ordering fail closed.
- The returned immutable snapshot records state, event count, bounded event-type history, and a fixed failure code.
- `execution_authorized` and `eligible_for_untrusted_execution` are always false.

## Limitations

This is not a runtime controller, process supervisor, timeout killer, VM broker, artifact collector, or cleanup implementation. The state machine records what a trusted adapter reports; it cannot independently prove that the adapter actually terminated a process or removed resources. That requires a separately trusted host implementation and independent acceptance evidence.

## Next work

1. Define a narrow host adapter protocol with fixed operation names and bounded typed inputs; no dynamic command execution.
2. Specify out-of-band host and external-canary identity authentication.
3. Add artifact path/size/digest collection contract and bind evidence to the signed acceptance report.
4. Threat-model cancellation races, timeout/kill semantics, cleanup retries, and crash recovery.
5. Keep real VM/provider operations gated behind separate explicit approval and independent security review.
