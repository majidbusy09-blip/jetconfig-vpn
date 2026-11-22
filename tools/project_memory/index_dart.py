#!/usr/bin/env python3
"""Build and verify a deterministic lexical index of the JET VPN Dart entrypoint.

This intentionally uses only Python's standard library. It is a navigation aid,
not a replacement for the Dart analyzer or a semantic call graph.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "lib" / "main.dart"
OUTPUT = ROOT / "docs" / "generated" / "jet_vpn_code_index.json"
STATUS = ROOT / "docs" / "CURRENT_STATUS.md"

IMPORT_RE = re.compile(r"""^\s*(import|export|part)\s+['"]([^'"]+)['"]""")
DECLARATIONS = (
    ("class", re.compile(r"^\s*(?:(?:abstract|base|final|sealed)\s+)?class\s+([A-Za-z_]\w*)")),
    ("enum", re.compile(r"^\s*enum\s+([A-Za-z_]\w*)")),
    ("mixin", re.compile(r"^\s*mixin\s+([A-Za-z_]\w*)")),
    ("extension", re.compile(r"^\s*extension(?:\s+type)?(?:\s+([A-Za-z_]\w*))?")),
)
CALLABLE_RE = re.compile(
    r"^\s{0,12}(?:(?:static|external|factory|abstract|covariant|const)\s+)*"
    r"(?:[A-Za-z_]\w*(?:<[^;\n{}]+>)?\??)\s+([A-Za-z_]\w*)\s*\("
)


def build_index() -> dict:
    raw = SOURCE.read_bytes()
    source = raw.decode("utf-8")
    lines = source.splitlines()
    imports = []
    symbols = []

    for number, line in enumerate(lines, start=1):
        match = IMPORT_RE.match(line)
        if match:
            imports.append({
                "directive": match.group(1),
                "uri": match.group(2),
                "line": number,
            })

        found = False
        for kind, pattern in DECLARATIONS:
            match = pattern.match(line)
            if match:
                symbols.append({
                    "kind": kind,
                    "name": match.group(1) or "(unnamed extension)",
                    "line": number,
                })
                found = True
                break

        if not found:
            match = CALLABLE_RE.match(line)
            if match:
                symbols.append({
                    "kind": "callable",
                    "name": match.group(1),
                    "line": number,
                })

    for symbol in symbols:
        token = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(symbol["name"]) + r"(?![A-Za-z0-9_])")
        symbol["reference_count"] = len(token.findall(source))

    try:
        import subprocess
        blob_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD:lib/main.dart"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        blob_sha = None

    return {
        "schema_version": 1,
        "generator": "tools/project_memory/index_dart.py",
        "analysis_mode": "lexical",
        "source": {
            "path": "lib/main.dart",
            "git_blob_sha": blob_sha,
            "utf8_bytes": len(raw),
            "unicode_code_points": len(source),
            "lines": len(lines),
        },
        "imports": imports,
        "symbols": symbols,
        "limitations": [
            "This is a deterministic lexical index, not a Dart AST.",
            "Reference counts are token occurrence counts, not verified call edges.",
            "Dynamic dispatch, generated code, extension resolution, and cross-file semantics are not resolved.",
        ],
    }


def verify_status(index: dict) -> list[str]:
    text = STATUS.read_text(encoding="utf-8")
    source = index["source"]
    problems = []
    blob = source["git_blob_sha"]
    if not blob or blob not in text:
        problems.append("docs/CURRENT_STATUS.md does not record the current lib/main.dart Git blob SHA.")
    expected = (
        f'{source["lines"]:,} lines / '
        f'{source["utf8_bytes"]:,} UTF-8 bytes / '
        f'{source["unicode_code_points"]:,} Unicode code points'
    )
    if expected not in text:
        problems.append(
            "docs/CURRENT_STATUS.md source metrics are stale or mislabeled; "
            f"expected: {expected}"
        )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Regenerate the committed index.")
    mode.add_argument("--check", action="store_true", help="Fail if the committed index differs.")
    parser.add_argument("--check-status", action="store_true", help="Verify CURRENT_STATUS source fingerprint.")
    args = parser.parse_args()

    index = build_index()
    rendered = json.dumps(index, ensure_ascii=False, indent=2) + "\n"

    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
        print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    else:
        if not OUTPUT.exists():
            print(f"Missing generated index: {OUTPUT.relative_to(ROOT)}", file=sys.stderr)
            return 1
        committed = OUTPUT.read_text(encoding="utf-8")
        if committed != rendered:
            print("Generated code index is stale. Run:", file=sys.stderr)
            print("python tools/project_memory/index_dart.py --write", file=sys.stderr)
            try:
                committed_data = json.loads(committed)
            except json.JSONDecodeError as error:
                print(f"Committed index is invalid JSON: {error}", file=sys.stderr)
                return 1
            for key in index:
                if committed_data.get(key) != index[key]:
                    if key == "symbols":
                        old_symbols = committed_data.get("symbols", [])
                        new_symbols = index["symbols"]
                        print(
                            f"Mismatch in symbols: committed={len(old_symbols)}, "
                            f"generated={len(new_symbols)}",
                            file=sys.stderr,
                        )
                        for position, (old_symbol, new_symbol) in enumerate(
                            zip(old_symbols, new_symbols)
                        ):
                            if old_symbol != new_symbol:
                                print(
                                    f"First symbol mismatch at index {position}: "
                                    f"committed={old_symbol!r}; generated={new_symbol!r}",
                                    file=sys.stderr,
                                )
                                break
                    else:
                        print(
                            f"Mismatch in {key}: committed={committed_data.get(key)!r}; "
                            f"generated={index[key]!r}",
                            file=sys.stderr,
                        )
            if committed_data == index:
                print("JSON data matches; only serialization/whitespace differs.", file=sys.stderr)
            return 1
        print("Generated code index matches the current source.")

    if args.check_status:
        problems = verify_status(index)
        if problems:
            for problem in problems:
                print(f"STALE MEMORY: {problem}", file=sys.stderr)
            return 1
        print("CURRENT_STATUS source fingerprint and metrics are current.")

    print(
        f'Indexed {len(index["symbols"])} symbols and '
        f'{len(index["imports"])} import/export/part directives; '
        f'{index["source"]["lines"]:,} lines, '
        f'{index["source"]["utf8_bytes"]:,} UTF-8 bytes.'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
