# Sandbox Artifact Collector Contract

## Purpose and boundary

`tools/task_orchestrator/sandbox_artifacts.py` defines a pure, in-memory validation contract for bounded artifacts associated with one sandbox attempt. It accepts typed candidate records and already-supplied byte strings. It does **not** open or enumerate filesystem paths, inspect inode types, resolve symlinks, retain or delete files, authenticate observers, verify report signatures, or execute code.

The module is a deterministic validator, not a trusted host collector. A caller-controlled `kind="regular_file"` field is only an assertion; it is not proof that a filesystem object is a regular file.

## Required bindings

Every manifest binds:
- attempt ID;
- runtime ID;
- policy SHA-256 digest;
- assembled evidence SHA-256 digest;
- signed acceptance-report SHA-256 digest;
- bounded retention duration;
- sorted artifact path, byte count, and recomputed SHA-256 digest.

The report digest is a content binding only. This module does not verify the report signature or establish that the report is trusted. The existing signed-report verifier and a future trusted host controller must independently establish that provenance.

## Path and object policy

- Only normalized, relative POSIX paths under `artifacts/` or `reports/` are accepted.
- Absolute paths, Windows drive paths, backslashes, NUL, empty components, dot components, parent traversal, duplicate paths, hidden/unsupported components, and overlong paths are rejected.
- Only the typed `regular_file` kind is accepted. Symlink, directory, device, and symlink-target declarations are rejected.
- The allowlisted path is a logical artifact name, not a path that this module opens.

## Resource and retention limits

| Limit | Value |
|---|---:|
| Artifact count | 64 |
| Per-artifact bytes | 256 KiB |
| Aggregate bytes | 2 MiB |
| Path bytes | 240 |
| Component bytes | 64 |
| Retention | 1 second to 30 days |

Empty artifact sets and empty files are rejected. Manifest entries are sorted by normalized path and serialized as canonical compact JSON. SHA-256 is recomputed from each supplied byte string and from the canonical manifest.

The retention field is policy metadata only. No storage, expiration timer, deletion, or retention enforcement is implemented here.

## Future trusted host implementation requirements

A real collector must be a separately reviewed host-side implementation and must not trust candidate path strings or caller-supplied object kinds. At minimum it must:
1. Anchor traversal to a pre-opened, trusted artifact root directory descriptor.
2. Walk components using descriptor-relative operations (for example, `openat` with `O_NOFOLLOW`) and reject `.`, `..`, absolute paths, mount crossings where policy requires, and unexpected path components.
3. Use `fstat` on the opened descriptor and accept only regular files; reject symlinks, directories, sockets, FIFOs, block/character devices, and hard-link cases outside the explicit policy.
4. Avoid time-of-check/time-of-use races by hashing and copying from the same already-open descriptor, enforcing size limits while streaming, and checking file identity/size before and after collection.
5. Recompute SHA-256 on the host, enforce file-count/per-file/aggregate limits before retaining content, and produce the same canonical manifest format.
6. Bind the manifest to the exact attempt, runtime, policy, evidence bundle, and independently verified signed acceptance report.
7. Enforce retention in a trusted storage layer with bounded quotas, deletion audit, crash recovery, and no guest/provider authority to extend retention or alter the manifest.
8. Keep artifacts quarantined and non-executable. Collection must not automatically apply patches, publish files, or change execution authorization.

A later integration must also decide whether artifact content is retained in the signed report or whether only manifest metadata and independently stored content digests are signed. Do not silently assume that adding a manifest digest to an existing report makes the report cryptographically bind the artifact bytes.

## Tests and safety flags

Unit tests use in-memory byte strings only. They cover traversal and allowlist rejection, symlink/directory/device rejection, duplicate paths, per-file and aggregate size limits, count limits, digest recomputation, deterministic ordering, metadata binding, and bounded retention.

This contract is not a filesystem collector and provides no proof of VM isolation, artifact provenance, observer authenticity, signature validity, or cleanup. Both `execution_authorized` and `eligible_for_untrusted_execution` remain `false`.
