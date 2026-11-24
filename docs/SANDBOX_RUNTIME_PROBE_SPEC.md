# Runtime Acceptance Probe Contract (Specification Only)

**Status:** static specification and inventory consistency tests only. This change does not execute probes, start processes, create network traffic, provision a VM, or authorize untrusted code.

## Purpose

Make the existing signed-report inventory operationally precise before implementing any runner. The manifest at `tools/task_orchestrator/runtime_probe_manifest.json` is the authoritative probe contract for the existing `sandbox_acceptance.REQUIRED_PROBES` inventory. Its tests enforce exact one-to-one inventory alignment.

## Evidence trust model

- The host controller owns enforcement observations: VM/kernel boundary, cgroups, mounts, devices, process termination, artifact collection, cleanup, and instance identity.
- The guest may emit bounded measurements for guest-local properties, but a guest report is never sufficient for host isolation, resource enforcement, or egress claims.
- An external canary in a separate trust/network domain observes attempted egress. It must use per-attempt nonces, timestamped append-only observations, and independently controlled credentials.
- Provider API status, provider-generated JSON, guest-generated success flags, and a signature over self-reported claims are not independent evidence.
- Every probe fails closed when its independent observer is unavailable, evidence is incomplete, or the observation cannot distinguish policy enforcement from an ordinary application error.

## Probe ownership and implementation notes

| Probe | Required observer | Key acceptance property |
|---|---|---|
| runtime_vm_boundary | Host controller | Guest VM boundary is independently distinct from host |
| dedicated_kernel | Host controller | Dedicated guest kernel, not shared host kernel |
| guest_non_root_no_capabilities | Guest + host | Non-root identity and no effective/permitted/inheritable/ambient/bounding capabilities |
| seccomp_enforced | Guest + host | Active filter plus harmless negative syscall test |
| cgroup_cpu_memory_pid_enforced | Host controller | Finite CPU, memory, PID caps; guest cannot raise them |
| disk_quota_enforced | Host controller | Finite enforced writable-layer quota |
| source_readonly_scratch_writable | Host + guest | Source rejects writes; bounded scratch accepts writes |
| host_home_secrets_absent | Host controller | No host home, credential, or secret mounts exposed |
| host_sockets_devices_absent | Host controller | No Docker/runtime/control sockets or unapproved devices |
| metadata_endpoint_blocked | External canary + host | Metadata test route is blocked and independently observed |
| ipv4_egress_blocked | External canary + host | No IPv4 canary connection |
| ipv6_egress_blocked | External canary + host | No IPv6 canary connection; unsupported IPv6 is not a pass |
| dns_udp_tcp_blocked | External canary + host | UDP and TCP DNS cannot reach authoritative canary |
| quic_udp443_blocked | External canary + host | UDP/443 egress is blocked |
| external_canary_unreachable | External canary | Fresh nonce is not observed across supported egress paths |
| wall_clock_timeout_enforced | Host controller | Host monotonic deadline terminates runtime |
| process_tree_kill_verified | Host controller | No descendant survives cancellation/timeout |
| artifact_path_size_digest_verified | Host controller | Allowlisted path, regular file, size ceiling, host-recomputed SHA-256 |
| cleanup_success_failure_timeout | Host controller | Resources removed for all three outcome classes |
| fresh_vm_no_prior_attempt_residue | Host controller | New instance and no cross-attempt marker leakage |

## Required evidence envelope

Each probe must eventually emit a bounded raw evidence record with: suite/version, probe ID, attempt ID, runtime instance ID, observer identity, monotonic start/end offsets, outcome, policy reference, and exact observation payload. The trusted host must collect and hash raw bytes; the guest must not choose the digest accepted by the verifier. The signed report must bind the exact host-collected evidence digest.

The existing verifier caps each evidence blob at 128 KiB and total evidence at 2 MiB. The future collector must stay within these limits and reject truncation, duplicate probe IDs, missing observations, stale timestamps, and mismatched attempt/runtime identities.

## Sequencing and gates

1. Implement deterministic fake-observer contract tests without starting guest code or opening sockets.
2. Implement the host controller as a trusted component with fixed, allowlisted probe definitions; no task-supplied shell command or dynamic probe code.
3. Implement a minimal guest probe binary/image separately, with read-only source and no credentials.
4. Implement external canary observation in a separate account/network trust domain.
5. Review the complete host/guest threat model and supply-chain provenance.
6. Only then request separate owner approval for a real VM pilot, data transfer, account, and spend.

GitHub-hosted Actions and the existing Bubblewrap benign self-test are not an accepted untrusted-code runtime. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.
