# Host-Side Sandbox Evidence Collector — Contract

**Status:** local contract and deterministic unit tests only. No runtime, VM, guest, process, socket, network request, provider, credential, or signing key is started or configured.

## Responsibility boundary

`sandbox_host_evidence.py` is an evidence assembler, not a Sandbox launcher or acceptance runner. It accepts typed observations from adapters that are supplied by a future trusted host controller. It cannot invoke commands, provision infrastructure, collect files from a guest, or contact an external canary.

The collector performs these checks:

1. Loads the repository-pinned 20-probe manifest and requires exact agreement with `sandbox_acceptance.REQUIRED_PROBES`.
2. Derives required trust domains from each probe's manifest owner.
3. Requires an explicit trusted observer identity set for each domain: `host_controller`, `guest`, and `external_canary`.
4. Binds every observation to one attempt ID and one known probe.
5. Rejects untrusted identities, unauthorized domains, duplicate domain observations, missing required observers, stale/future timestamps, malformed outcomes, and oversized or empty payloads.
6. Serializes the raw observer payloads in a deterministic bounded evidence envelope and recomputes SHA-256 on the host side.
7. Preserves a failed observation as a failed probe. It never upgrades missing or failed evidence to a pass.

The returned bundle is immutable at the mapping boundary and always sets both execution-authorization flags to false.

## Trust model

The observer identity sets are supplied by the caller; this module does not authenticate those identities. In production, their provisioning and rotation must be protected out-of-band and independently reviewed. A provider-generated ID, guest claim, environment variable, or value stored inside the guest is not a trust anchor.

The guest domain is accepted only for probes whose manifest explicitly requires guest-local evidence, and never as a substitute for host or external-canary evidence. External network probes require the separately controlled canary domain. The host controller must obtain canary observations through a separately authenticated channel and bind the same attempt ID and nonce.

## Evidence format and limits

Each assembled probe evidence blob contains the attempt ID, probe ID, observer domain/identity, UTC observation time, outcome, base64 raw payload, and a recomputed payload SHA-256. The assembled bytes are deterministic JSON and fit the existing verifier's per-probe 128 KiB and aggregate 2 MiB ceilings. Raw observer payloads are capped at 48 KiB each.

## What this does not prove

- It does not prove a VM or dedicated-kernel boundary.
- It does not enforce seccomp, cgroups, disk quotas, mounts, network egress, process termination, or cleanup.
- It does not verify observer identity cryptographically.
- It does not create or verify the final signed acceptance report.
- It does not change `execution_authorized: false` or `eligible_for_untrusted_execution: false`.

## Next implementation steps

1. Define a host-controller adapter interface whose only inputs are fixed probe IDs and bounded policy data; do not accept task-supplied shell commands or dynamic code.
2. Add deterministic contract tests for adapter lifecycle and timeout/cleanup state transitions, without launching processes.
3. Design out-of-band observer identity provisioning and authenticated external-canary evidence.
4. Perform threat-model and supply-chain review before any real runtime pilot.
5. Request separate approval before accounts, paid VM provisioning, private-source transfer, provider credentials, or spend.

GitHub-hosted Actions and the benign Bubblewrap self-test remain non-accepted execution environments.
