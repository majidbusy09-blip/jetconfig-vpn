# Provider-neutral Dispatcher Core

## Purpose
The dispatcher connects a validated task envelope to one explicitly registered
provider adapter and returns a metadata-only audit record. Provider selection is
made by trusted host configuration; task or Issue content cannot select an
arbitrary implementation.

## Current implementation boundary
- Calls the existing immutable, read-only adapter contract.
- Validates the task envelope and provider result before accepting the result.
- Requires the returned provider identity to match the registered provider.
- Records an envelope digest, context fingerprints, result status, changed paths,
  patch reference, requested verification profiles, and timestamps.
- Does not retain raw prompts, source text, secrets, or provider transcripts.
- Never applies patches, executes commands, accesses GitHub, or creates PRs.
- The fixture provider is suitable only for deterministic tests.

## What is deliberately not enabled
This is not a live OpenAI/Grok integration and is not an OS sandbox. A production
host must provide an explicitly configured adapter, credential handling outside
the repository, budget enforcement, cancellation/timeouts, and a disposable
isolated runtime. Network access and source transfer remain disabled until the
user explicitly authorizes a specific provider, data scope, and cost boundary.

## Next integration gates
1. Add a local host runner that accepts a previously verified handoff and
   constructs the provider registry from trusted configuration.
2. Add artifact transport for patch bytes, then pass them to
   `validate_completed_patch`; do not apply the patch yet.
3. Add isolated workspace execution and fixed verification profiles.
4. Add provider-specific adapters only after their data-transfer and cost
   boundaries are explicitly configured.
5. Keep PR creation, merge, release, and deployment as separate gated actions.
