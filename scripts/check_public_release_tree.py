#!/usr/bin/env python3
"""Check a public Git tree for high-risk tracked files, without reading clinical rows.

This gate cannot validate redistribution rights, old commits, or cached PRs.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path
import subprocess

BINARY_DATA_SUFFIXES = (
    ".parquet", ".arrow", ".feather", ".sqlite", ".sqlite3",
    ".db", ".pickle", ".pkl", ".sav", ".zip", ".7z",
)
HISTORICAL_AGGREGATES = frozenset((
    "dataset/MRI_CT_Race_Summary_with_pvalues.csv",
    "dataset/MRI_CT_Summary_with_pvalues.csv",
    "dataset/df_tot_CPT_codes.csv",
))
PRIVATE_PATTERNS = (
    "results/*", "*/results/*", "*LOCAL_ONLY*", "*INTERNAL_ONLY*",
    "*full_reconstruction_private*", "*.env", "*.env.*", "*.pem",
    "*.key", "*credential*", "*secrets*", "*patient_level*",
)


def tracked_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return sorted(p.decode("utf-8") for p in result.stdout.split(b"\0") if p)


def inspect_paths(root: Path, paths: list[str]) -> list[tuple[str, str]]:
    issues = []
    for path in paths:
        normal = path.replace("\\", "/")
        lower = normal.lower()
        reason = None
        if lower.endswith(BINARY_DATA_SUFFIXES):
            reason = "binary or archived data file"
        elif normal in HISTORICAL_AGGREGATES:
            reason = "historical study aggregate requiring release review"
        elif any(fnmatch.fnmatch(normal, pat) for pat in PRIVATE_PATTERNS):
            reason = "private or potentially sensitive path"
        elif lower.endswith(".ipynb"):
            try:
                obj = json.loads((root / path).read_text(encoding="utf-8"))
                cells = obj["cells"]
                if not isinstance(cells, list):
                    raise ValueError("Notebook cells not a list")
                if any(c.get("outputs") or c.get("execution_count") is not None
                       for c in cells if c.get("cell_type") == "code"):
                    reason = "notebook contains saved execution outputs or counts"
            except (OSError, UnicodeError, json.JSONDecodeError, KeyError, ValueError, TypeError):
                reason = "notebook cannot be safely parsed"
        if reason:
            issues.append((normal, reason))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    paths = tracked_paths(args.root.resolve())
    issues = inspect_paths(args.root.resolve(), paths)
    print("PUBLICATION TRACKED-FILE GATE:", "FAIL" if issues else "PASS")
    print("Tracked paths reviewed:", len(paths))
    print("Flagged paths:", len(issues))
    for name, reason in issues:
        print("FLAG:", name, "-", reason)
    print("This gate does not clear Git history, cached PRs, or dataset release rights.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
