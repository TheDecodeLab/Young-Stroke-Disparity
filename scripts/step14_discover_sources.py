"""Step 14: locate likely original source exports from local file metadata.

Scans only an explicitly selected root directory. Inspects Parquet schemas
and CSV headers, never patient records. Results contain relative file names,
column names and Parquet row counts; review locally before sharing.

Matching a schema does NOT prove that a file is an original TriNetX export,
that the data are approved for analysis, or that encounter linkage is valid.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", "results", "node_modules"}
KEYS = {
    "diagnoses": {"patient_id", "code", "date", "principal_diagnosis_indicator"},
    "procedures": {"patient_id", "code", "date"},
    "demographics": {"patient_id", "sex", "year_of_birth"},
}
HINTS = {
    "diagnoses": ("diagnos", "dx", "condition"),
    "procedures": ("procedur", "px", "cpt"),
    "demographics": ("demograph", "patient", "person"),
}
ENCOUNTERS = {"encounter_id", "visit_id", "admission_id", "visit_occurrence_id", "encounter_num", "encounter_number"}


def classify(columns: list[str], name: str) -> list[dict]:
    """Report schema candidates without treating filename matches as proof."""
    normalized = {column.lower().strip() for column in columns}
    lower_name = name.lower()
    scored = []
    for kind, expected in KEYS.items():
        matches = sorted(expected & normalized)
        missing = sorted(expected - normalized)
        hint = any(token in lower_name for token in HINTS[kind])
        # Label candidates with two or more expected columns, or
        # a filename hint plus at least one expected column.
        if len(matches) < 2 and not (hint and matches):
            continue
        score = len(matches) / len(expected)
        if hint:
            score += 0.1
        if kind == "procedures" and "principal_diagnosis_indicator" in normalized:
            score -= 0.3
        scored.append({
            "kind": kind,
            "schema_complete": not missing,
            "matched_required": matches,
            "missing_required": missing,
            "filename_hint": hint,
            "score": round(score, 3),
        })
    return sorted(scored, key=lambda v: (-v["score"], v["kind"]))


def schema_metadata(path: Path) -> dict:
    """Read Parquet metadata or CSV header only; no patient-level rows."""
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(path)
        return {"format": "parquet", "columns": pf.schema_arrow.names,
                "row_count": int(pf.metadata.num_rows)}
    if suffix == ".csv":
        import pandas as pd
        cols = pd.read_csv(path, nrows=0).columns.tolist()
        return {"format": "csv", "columns": cols, "row_count": None}
    raise ValueError("Only Parquet and CSV sources supported")


def discover(root: Path, max_depth: int = 4, max_files: int = 2000,
             max_candidates: int = 100) -> dict:
    """Walk a chosen root without following symlinks; cap work and output."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Search directory not found: {root}")
    if max_depth < 0 or max_files < 1 or max_candidates < 1:
        raise ValueError("Depth must be nonnegative and file limits must be positive")
    considered = 0
    inspected = 0
    errors = 0
    candidates = []
    limited = False
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        depth = len(Path(current).relative_to(root).parts)
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        if depth >= max_depth:
            dirs[:] = []
        for name in sorted(files):
            if not name.lower().endswith((".parquet", ".csv")):
                continue
            path = Path(current) / name
            if path.is_symlink() or not path.is_file():
                continue
            if considered >= max_files:
                limited = True
                break
            considered += 1
            try:
                meta = schema_metadata(path)
                inspected += 1
                groups = classify(meta["columns"], name)
                if groups:
                    candidates.append({
                        "relative_path": str(path.relative_to(root)),
                        "format": meta["format"],
                        "parquet_row_count": meta["row_count"],
                        "columns": meta["columns"],
                        "candidate_groups": groups,
                        "encounter_key_candidates": sorted(
                            set(x.lower() for x in meta["columns"]) & ENCOUNTERS),
                    })
            except (OSError, ValueError, ImportError, RuntimeError):
                errors += 1
        if limited:
            break
    candidates.sort(key=lambda c: (-max(z["score"] for z in c["candidate_groups"]),
                                   c["relative_path"]))
    omitted = max(len(candidates) - max_candidates, 0)
    return {
        "stage": "SOURCE_DISCOVERY_METADATA_ONLY",
        "root_label": root.name,
        "files_considered": considered,
        "file_schemas_read": inspected,
        "unreadable_files_n": errors,
        "stopped_at_max_files": limited,
        "candidate_matches_total": len(candidates),
        "candidate_matches_omitted_from_report": omitted,
        "candidates": candidates[:max_candidates],
        "warnings": [
            "The paths shown are relative to the selected local search root.",
            "Candidate labels are heuristics, NOT verification of original exports.",
            "The report includes filenames and field names. Review locally before sharing.",
            "CSV headers and Parquet metadata were inspected; patient data values were not read.",
            "Some partitioned Parquet directories or unsupported formats may be missed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True,
                        help="Explicit local directory to scan (do not use system root)")
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--max-files", type=int, default=2000)
    parser.add_argument("--max-candidates", type=int, default=100)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/phase1/source_candidates.json")
    args = parser.parse_args()
    result = discover(args.root, args.max_depth, args.max_files,
                      args.max_candidates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("Metadata-only report:", args.output)
    print("File schemas read:", result["file_schemas_read"])
    print("Candidate matches:", result["candidate_matches_total"])
    if result["stopped_at_max_files"]:
        print("WARNING: --max-files limit reached before scanning the whole root")
    print("Review source paths and approvals before Step 13; no original cohort reconstructed.")


if __name__ == "__main__":
    main()
