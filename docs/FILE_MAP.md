# JET VPN — Verified Repository File Map

> Snapshot: `main` at `47949178016a6ef3e855a215550b06f4eae8378d`, 2026-11-22. Recursive Git tree was not truncated; it contained 13 entries (8 files and 5 directories).

| Path | Verified purpose |
|---|---|
| `AGENTS.md` | Mandatory operating instructions for AI agents/contributors; added in this PR. |
| `README.md` | Project overview; may describe wider JetConfig ecosystem not included in this repository. |
| `pubspec.yaml` | Flutter package metadata, version, SDK constraint, dependencies. |
| `lib/main.dart` | Main Flutter application; UI, account, payment, server, VPN connection/recovery, settings and update logic. |
| `.github/workflows/build.yml` | Production build and automatic GitHub Release workflow. |
| `.github/workflows/pr-validation.yml` | Isolated validation workflow proposed in PR #2; not present on `main` until merged. |
| `tools/v2ray_notif_patch/apply_patch.sh` | Applies repository-maintained native patch to dependency sources in build workspace. |
| `tools/v2ray_notif_patch/V2rayCoreManager.java` | Patched V2Ray core manager source. |
| `tools/v2ray_notif_patch/V2rayProxyOnlyService.java` | Patched proxy-only service source. |
| `tools/v2ray_notif_patch/V2rayVPNService.java` | Patched VPN service source, including user-initiated notification disconnect marker. |

## Confirmed absences in this snapshot

The recursive `main` tree did not contain `android/`, `test/`, `pubspec.lock`, backend PHP sources, bot sources, worker sources, or JET VPN TV sources. CI may generate Android scaffold files in its temporary workspace; that does not make them tracked repository files.

## Source identity

- `lib/main.dart`: blob `df2914b2954d723869e4196d96f96b050618985a`, 9,002 lines, 336,260 characters.
- `pubspec.yaml`: blob `adc3b22a4538db4738bec789e3c3badf26e4f710`, version `2.4.5+284`.
- `tools/v2ray_notif_patch/apply_patch.sh`: blob `ef603a667eded4786dd12c2fefd3650667d12ba3`.
- `tools/v2ray_notif_patch/V2rayVPNService.java`: blob `fb081e7a99b076f7bbcda47b736b8571bb12966f`.

Never add paths to this map unless verified from the current tree or a separately identified source repository.
