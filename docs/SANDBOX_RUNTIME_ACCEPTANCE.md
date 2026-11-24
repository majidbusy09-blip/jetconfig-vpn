# Sandbox Runtime Acceptance Evidence Contract

## Purpose

This contract defines the independent evidence required before a candidate VM runtime can be considered for any future untrusted-code pilot. It is deliberately separate from the provider adapter and from `sandbox_contract.py`.

The provider must not generate or sign its own pass/fail report. A separately controlled acceptance suite runs fixed probes against the actual VM, writes bounded raw evidence, and signs a canonical report with a signing key unavailable to the provider and guest. The orchestrator pins the suite version and trusted public-key identity out of band.

## Implemented verifier

`tools/task_orchestrator/sandbox_acceptance.py` verifies:

- Strict UTF-8 canonical JSON, duplicate-key rejection, exact schema, exact suite ID/version, and report/signature size caps.
- Pinned provider, region, task, attempt, image digest, policy digest, and signing key ID.
- Fresh UTC timestamps, bounded suite duration, and limited clock skew.
- The exact required probe inventory, with no missing, duplicate, unknown, or failed probes.
- A SHA-256 evidence digest for each probe, recomputed against the exact raw evidence bytes supplied to the verifier.
- Exact raw-evidence inventory matching, non-empty evidence blobs, a 128 KiB per-probe cap, and a 2 MiB aggregate cap.
- A signature through an injected trusted verifier.

The module always returns `execution_authorized: false` and `eligible_for_untrusted_execution: false`. A passing report is not an execution authorization.

## Required independent probes

| Probe | Required evidence |
|---|---|
| `runtime_vm_boundary` | Actual one-task VM boundary, not a shared-kernel container |
| `dedicated_kernel` | Guest kernel identity differs from host and other concurrent guests |
| `guest_non_root_no_capabilities` | Non-root identity and no extra Linux capabilities/privileged mode |
| `seccomp_enforced` | Active Seccomp profile and negative syscall probes |
| `cgroup_cpu_memory_pid_enforced` | Enforced CPU, memory, and PID limits, not merely configured values |
| `disk_quota_enforced` | Enforced disk quota and write-overflow rejection |
| `source_readonly_scratch_writable` | Read-only source mount and isolated writable scratch |
| `host_home_secrets_absent` | Host home, environment secrets, signing files, and credentials inaccessible |
| `host_sockets_devices_absent` | Runtime sockets, host devices, and privileged interfaces inaccessible |
| `metadata_endpoint_blocked` | Cloud metadata and instance identity endpoints unreachable |
| `ipv4_egress_blocked` | IPv4 outbound traffic denied from guest |
| `ipv6_egress_blocked` | IPv6 outbound traffic denied from guest |
| `dns_udp_tcp_blocked` | External DNS over UDP and TCP denied |
| `quic_udp443_blocked` | QUIC/HTTP3 UDP 443 bypass denied |
| `external_canary_unreachable` | Independent external canary confirms no guest egress |
| `wall_clock_timeout_enforced` | Wall-clock budget is enforced by the control plane |
| `process_tree_kill_verified` | Timeout/cancel kills descendants and detached processes |
| `artifact_path_size_digest_verified` | Export path allowlist, size cap, and exact-byte digest enforced |
| `cleanup_success_failure_timeout` | Termination and destruction confirmed on success, failure, and timeout |
| `fresh_vm_no_prior_attempt_residue` | New attempt cannot observe prior attempt state or residue |

Every probe must produce a bounded evidence object whose exact bytes are SHA-256 hashed and included in the signed report. The verifier also requires the corresponding raw evidence bundle and recomputes every digest; a digest string alone is insufficient. Each blob is limited to 128 KiB and the complete bundle to 2 MiB. A bare provider API response or a self-reported capability flag is not acceptable evidence.

## Trust and signature requirements

- The suite signing key must be controlled outside the provider and guest trust domain.
- Production verification must use an out-of-band pinned public key and an audited asymmetric signature implementation (for example, Ed25519).
- The verifier interface is injected into `verify_signed_acceptance_report`; this repository change does not provision the key, choose a crypto dependency, or install a production verifier.
- The test verifier is a test double only and is not cryptographic security.
- The signed bytes must be canonical JSON (UTF-8, sorted keys, compact separators, no duplicate keys). The signature covers the exact canonical bytes.
- Reports are bound to provider, region, runtime, task, attempt, image, policy, suite version, and UTC timestamps. Stale or replayed reports are rejected.

## Security boundary and remaining work

The verifier now binds each signed digest to the supplied raw evidence bytes and rejects missing, extra, empty, altered, or oversized evidence. This still validates evidence supplied by a separate suite; it does not establish that the suite itself is honest or independently executed. This PR implements the report verifier and adversarial unit tests only. It does not implement the actual guest probe runner, provider adapter, signing service, key distribution, VM provisioning, or runtime attestation. Therefore no candidate runtime has passed these checks yet.

Before a pilot:
1. Build and independently review the fixed guest probe suite and external canary controller.
2. Establish a signing service/key outside the provider and guest, with rotation and revocation.
3. Implement an audited Ed25519 verifier backed by a pinned public key and key ID.
4. Run the suite against the exact provider, region, VM image, and network policy intended for the pilot.
5. Preserve raw probe evidence, signature, verifier version, timestamps, runtime identity, and cleanup proof.
6. Require explicit owner approval for any account, payment method, source transfer, sandbox provisioning, provider spend, or untrusted-code pilot.

No private source, model output, credentials, API keys, production secrets, or paid service is used by these tests.


## Pinned trust-store policy adapter (implementation status)

`tools/task_orchestrator/sandbox_trust.py` adds a fail-closed trust-store policy adapter that implements the existing `SignatureVerifier` shape:

- Requires canonical UTF-8 JSON with an exact schema and no duplicate keys.
- Requires the trust-store SHA-256 digest to be supplied independently by protected configuration; the digest stored beside the trust-store file is not trusted.
- Requires a caller-supplied minimum trust-store version. The caller must advance this value monotonically in protected configuration; the module does not persist anti-rollback state.
- Allows at most 64 unique key IDs and accepts only Ed25519 public keys of exactly 32 bytes.
- Enforces key status (`active` only) and UTC validity windows; retired, revoked, unknown, not-yet-valid, and expired keys fail closed.
- Delegates signature mathematics to an injected `Ed25519Backend`. The test backend is deterministic test scaffolding, not cryptography.

**Important limitation:** this is trust-store parsing, pinning, version-floor, and key-selection policy. It is not a production Ed25519 implementation, does not load keys from a remote service, does not store rollback state, and does not create or rotate private keys. A production caller still needs an audited cryptographic backend and protected out-of-band configuration for the trust-store digest and monotonic version floor.

Before production integration, independently review how the digest/version floor are provisioned and updated, how trust-store changes are authorized, and how emergency revocation propagates. A trust-store update must be reviewed and its new digest and minimum version deployed atomically through a protected control plane.
