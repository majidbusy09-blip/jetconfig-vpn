# ADR-002 — Managed sandbox candidate evaluation

- **Status:** No managed sandbox candidate is currently eligible for the intended pilot under the owner's present no-payment/no-account/no-test constraints
- **Date:** 2026-11-24 (reassessment)
- **Scope:** Reassessment of the PR #20 worker-runtime candidate decision
- **Evidence type:** public vendor documentation reviewed; no tenant, API key, sandbox, or workload has been created

## Initial evaluation (superseded by the 2026-11-24 reassessment)

The original evaluation selected E2B as the first candidate for a harmless pilot and kept Daytona as an alternative. That recommendation is historical only and must not be used as current authorization. See the reassessment block below for the current decision.

Why E2B first:
- E2B documents one Firecracker microVM per sandbox, with a dedicated guest kernel and hypervisor-enforced isolation.
- Its API exposes explicit outbound network disablement and allow/deny rules.
- It documents explicit timeout behavior, kill/shutdown, and sandbox lifecycle APIs.
- Public pricing currently lists a free Hobby tier with one-time credits, limited runtime and concurrency, which could support a tightly bounded pilot without choosing a paid plan. Actual costs must be checked before any use.

## Evidence comparison

| Criterion | E2B | Daytona |
|---|---|---|
| Runtime boundary | Vendor documents one Firecracker microVM per sandbox, dedicated kernel, no shared customer kernel/filesystem/memory. | Vendor documents hardware-isolated VMs with dedicated kernel; Linux VM uses Firecracker. Important: Linux container is the default class and shares the host kernel; the VM class must be selected explicitly. |
| Egress | `allowInternetAccess=false` blocks outbound internet. Fine-grained `denyOut` / `allowOut` also documented. | `networkBlockAll` and allow lists documented, but egress is open by default. Tier 1/2 policies cannot be overridden per sandbox; Tier 3/4 allow sandbox-level strict policy. |
| Network caveats | Domain filtering is limited to HTTP Host on port 80 and TLS SNI on 443; QUIC/HTTP3 is not covered by domain rules. Domain filtering automatically permits 8.8.8.8 unless `dnsServers: []` is explicitly set; that resolver permission allows all traffic to that IP, not DNS alone. For the pilot, disable all internet access rather than rely on domain allowlists. | Network controls are configurable, but actual policy depends on organization tier. Must prove `networkBlockAll` takes effect for the chosen account and inspect all routes. |
| Lifecycle | Timeout can kill the sandbox; explicit `kill()` documented. Hobby continuous runtime up to 1 hour; Pro up to 24 hours. Paused sandboxes can persist indefinitely, so pause/resume must not be used for disposable worker attempts. | Supports ephemeral sandboxes and wall-clock TTL. Delete is asynchronous by default; callers must wait for the `destroyed` state. Ephemeral Linux VM and VM snapshots have documented constraints. |
| Secrets / credentials | E2B documents secret injection through an egress proxy. Do not use secrets for this pilot; no credential should enter the sandbox. | A `write:sandboxes` API key can mount organization secrets; host allowlists are critical. Any valid organization API key can access the toolbox of running sandboxes regardless of selected resource scopes. This needs a dedicated organization/project and careful trust-boundary review. |
| Region / residency | E2B advertises EU regions; its status page lists EU-West-1. Obtain and review the current DPA, subprocessors, retention and exact region placement before uploading private source. | Region and organization controls exist; verify the actual target region and contract/data terms before source upload. |
| Cost | Public pricing lists Hobby at $0/month with a one-time $100 credit, up to 10 concurrent sandboxes and 1 hour continuous runtime; Pro is $150/month plus usage. A card verification may be requested in some cases. Set spend limits and monitor usage. | Billing and resource limits depend on organization tier and sandbox class. Obtain exact pricing/limits before provisioning. |

## Pilot configuration — proposed, not executed

1. Create a dedicated vendor project/organization only after owner approval. Do not reuse a personal workspace containing unrelated secrets or sandboxes.
2. Use a short-lived API key held only by the trusted control plane. Never pass the vendor API key, GitHub token, model-provider key, SSH key, signing file, or production credential into the sandbox.
3. Create exactly one Linux Firecracker microVM per attempt from a pinned, reviewed image/template. Do not use a shared-kernel container.
4. Set a short hard timeout with timeout action `kill`; do not pause, snapshot, fork, or persist the attempt. Explicitly call kill during cleanup and confirm the provider reports the sandbox destroyed/terminated.
5. Disable all outbound internet at creation. Do not allow GitHub, package registries, arbitrary DNS, metadata endpoints, or public ingress during the initial test.
6. Upload only a small, synthetic test fixture. Do not upload the private JET VPN repository yet.
7. Run a fixed harmless acceptance program that tests its own UID, source/workspace boundaries, process and resource limits, and network denial. Attempt harmless denied outbound connections and record evidence.
8. Test cancellation and timeout with a benign child process tree; confirm descendants terminate and the sandbox is destroyed. Test cleanup after success, failure, timeout, and API interruption.
9. Export only a bounded test artifact. Independently verify size, digest, path policy, and lifecycle metadata in the existing orchestrator. Do not apply patches.
10. Repeat the acceptance suite and retain evidence. Any missing control, ambiguous result, or cleanup failure means **blocked**.

## Explicit caveats

- Vendor documentation is a description of the provider's product, not independent proof that our exact account, plan, region, API configuration, and runtime enforce every required property.
- The E2B network default is open. The pilot must explicitly set no internet access. If domain allowlists are ever considered, test DNS and non-HTTP protocols; do not assume hostname rules cover QUIC/HTTP3 or arbitrary ports.
- A vendor microVM does not remove the need for our own patch validation, bounded artifact handling, audit log, independent verification, and human review.
- Before any private repository source is uploaded, review the DPA, subprocessors, data location, retention/deletion guarantees, security report, and contractual terms.

## Approval boundary

No account, key, subscription, payment method, sandbox, runner, provider integration, private source upload, model execution, or spend has been created or authorized by this decision record. A separate explicit approval is required before creating an account/project, entering credentials, accepting paid terms, or incurring charges.

PR #20 is merged. No production app, bot, payment, backend, server, signing, release, or deployment behavior is in scope.

## Reassessment evidence and current block — 2026-11-24

- E2B's official security guidance states that customers should contact E2B before running tests and obtain prior written consent. The EU region is Google Cloud `europe-west1`; workspace verification requires adding a payment method. These are hard blockers for the currently authorized no-account/no-payment pilot.
- E2B outbound internet is open by default. The documented `allowInternetAccess=false` setting is the appropriate initial deny-all control; hostname allowlists have HTTP Host/TLS SNI limitations and DNS resolver exceptions. Do not rely on domain allowlists for the first acceptance run.
- Daytona distinguishes Linux containers (shared host kernel) from Linux VM sandboxes (dedicated guest kernel). The strict sandbox-level `networkBlockAll` control is restricted to Tier 3/4. The documented Tier 3 route requires a $500 top-up, which is outside the current authorization.
- No account, key, payment method, sandbox, workload, private-source transfer, provider connection, or spend has been created or approved.
- These findings do not prove any account-specific runtime configuration. If constraints change, repeat vendor-documentation and contract review before any pilot.

PR #20 is merged; PRs #38–#44 are merged through main `f682c56331bfb7c07bc4c5be26fddc33a3043969`. The provider decision remains blocked and no production behavior changed.
