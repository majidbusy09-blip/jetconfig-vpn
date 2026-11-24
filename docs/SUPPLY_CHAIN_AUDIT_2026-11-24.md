# Sandbox Crypto Dependency Supply-Chain Review — 2026-11-24

**Scope:** read-only review of the three exact pins in `tools/task_orchestrator/requirements-sandbox-crypto.txt`. No versions, install commands, or trust decisions are changed by this report.

## Findings

| Package pin | PyPI release evidence | SHA-256 evidence surfaced | Assessment |
|---|---|---|---|
| `cryptography==50.0.2` | PyPI reports provenance for all 59 release files; uploaded 2026-09-30 using Trusted Publishing | The source archive SHA-256 is `7b46165bb56eb4704e2eaaf86f3c940d19154535d9b0ca7d6d590b04060e00d5` | Strongest provenance signal in this set. The actual wheel selected by the CI runner still needs an exact wheel hash in the platform-specific lock. |
| `cffi==2.1.1` | PyPI reports no provenance for any of the 100 release files; uploaded 2026-08-03 using Twine, not Trusted Publishing | Source archive SHA-256: `dd31f52ea1086513bb9df30f8fcee9b8918323ae067a3d5b78bc826a000712be` | Provenance gap. A version pin and digest can provide artifact integrity but cannot establish publisher/build origin. |
| `pycparser==3.12` | PyPI reports no provenance for either release file; uploaded 2026-10-22 using uv/0.5.13, not Trusted Publishing | Wheel SHA-256: `a076f3f489b39b43ed13563a1dafe42447445bec2e294154ec5c57fcdda4c85e`; source SHA-256: `f03387877eab82ce01bbdfd0ba7252ee55a90b1c708d5129e2ce915475cf1db6` | Provenance gap. The wheel is pure Python, but still requires hash pinning and source/release review. |

Sources:
- https://pypi.org/project/cryptography/50.0.2/
- https://pypi.org/project/cffi/2.1.1/
- https://pypi.org/project/pycparser/3.12/
- https://docs.pypi.org/using-pypi/package-security/provenance/

## Important distinction

A SHA-256 hash lock prevents an unexpected artifact from being installed when the expected hash is independently committed and reviewed. It does **not** prove that the publisher, build workflow, source commit, or build environment is trustworthy. PyPI attestations/provenance address origin and build claims; PyPI documents that provenance can be verified, while absence of provenance does not by itself mean a package is malicious.

## Safe next actions

1. Keep the existing exact version pins unchanged until the CI target matrix is explicit.
2. Determine the actual wheel tags selected by each workflow (currently Python 3.12 on Ubuntu hosted runners; the workflow also installs the same file in both orchestrator and APK validation jobs).
3. Capture the exact selected wheel filenames and hashes for every supported OS/Python/architecture combination. Use only binary wheels in CI and install with `--require-hashes` once the complete supported artifact set is independently verified.
4. Verify PyPI attestations for the exact cryptography wheel actually selected, not merely the release landing page. Record the verification identity and transparency-log evidence.
5. For cffi and pycparser, retain hashes but explicitly record the provenance gap; review upstream source tags, release history, maintainer/publishing controls, and compare downloaded artifact contents to the corresponding source release. Do not claim cryptographic provenance where none exists.
6. Consider whether `pycparser` is required at runtime or only as a transitive dependency of the selected cffi/cryptography build. Do not remove it without a reproducible dependency-resolution and test result.
7. Add a CI check that fails if the resolved dependency graph contains an unpinned package or selects an artifact outside the reviewed hash set.

## Not done / not claimed

- No complete wheel hash lock has been generated; this report intentionally does not guess wheel hashes.
- No PyPI attestation signature has been independently verified in this review; the report records PyPI's displayed provenance status only.
- No dependency was upgraded, downgraded, removed, or newly installed.
- No package is declared safe solely because it has a hash or provenance badge.
- No provider, VM, KMS/HSM, private source transfer, or untrusted code execution is authorized.
