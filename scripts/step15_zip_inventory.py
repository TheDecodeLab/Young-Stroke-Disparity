"""Step 15: inventory a local TriNetX export ZIP without extracting it.

Reads archive metadata and the FIRST LINE of CSV/TSV member files only.
Does not inspect any patient-level rows or save member content. It must
run locally on an authorized data workstation. The result includes source
member names and column names: review the report before sharing.

This is a metadata inventory, not a source validation or cohort builder.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    "diagnoses": {"patient_id", "code", "date", "principal_diagnosis_indicator"},
    "procedures": {"patient_id", "code", "date"},
    "demographics": {"patient_id", "sex", "year_of_birth"},
}
HINTS = {
    "diagnoses": ("diagnos", "condition", "_dx", "/dx"),
    "procedures": ("procedur", "_px", "/px"),
    "demographics": ("demograph", "patient", "person"),
}
ENCOUNTERS = {
    "encounter_id", "visit_id", "admission_id", "visit_occurrence_id",
    "encounter_num", "encounter_number", "encounterid", "visitid",
}
SUPPORTED = {".csv": ",", ".tsv": "\t"}


def classify(columns: list[str], member: str) -> list[dict]:
    """Rank schema matches, without assuming names or roles are definitive."""
    fields = {col.strip().lower() for col in columns}
    name = member.lower()
    matches = []
    for kind, required in FIELDS.items():
        matched = sorted(required & fields)
        missing = sorted(required - fields)
        hint = any(key in name for key in HINTS[kind])
        if len(matched) >= 2 or (hint and matched):
            score = len(matched) / len(required) + (0.1 if hint else 0)
            # The shared patient_id/code/date schema is not enough to tell
            # procedure from diagnosis; report both until codebook verified.
            if kind == "procedures" and "principal_diagnosis_indicator" in fields:
                score -= 0.3
            matches.append({
                "kind": kind,
                "schema_complete": not missing,
                "matched_fields": matched,
                "missing_fields": missing,
                "filename_hint": hint,
                "score": round(score, 3),
            })
    return sorted(matches, key=lambda v: (-v["score"], v["kind"]))


def safe_member_header(zf: ZipFile, info: ZipInfo, limit: int = 65536) -> list[str] | None:
    """Read at most 64 KiB of decompressed text; never read patient rows.

    A header longer than the limit is left unparsed rather than consuming
    data records. The file-like object is closed before examining next member.
    """
    ext = PurePosixPath(info.filename).suffix.lower()
    if ext not in SUPPORTED:
        return None
    with zf.open(info, "r") as raw:
        data = raw.readline(limit + 1)
    if len(data) > limit or (data and not data.endswith((b"\n", b"\r")) and info.file_size > len(data)):
        raise ValueError("CSV/TSV header too long or incomplete")
    header = data.decode("utf-8-sig", errors="replace")
    return next(csv.reader(io.StringIO(header), delimiter=SUPPORTED[ext]), [])


def inspect_zip(path: Path, max_members: int = 2000, max_results: int = 150) -> dict:
    """Inspect a ZIP central directory and CSV/TSV headers (no extraction)."""
    if max_members < 1 or max_results < 1:
        raise ValueError("Member and result caps must be positive")
    if not path.is_file():
        raise FileNotFoundError(f"Archive not found: {path}")
    candidates = []
    counted_ext: dict[str, int] = {}
    skipped_headers = 0
    encrypted_members = 0
    with ZipFile(path, "r") as zf:
        members = [m for m in zf.infolist() if not m.is_dir()]
        for info in members:
            ext = PurePosixPath(info.filename).suffix.lower() or "(none)"
            counted_ext[ext] = counted_ext.get(ext, 0) + 1
        selected = members[:max_members]
        for member in selected:
            ext = PurePosixPath(member.filename).suffix.lower()
            if ext not in SUPPORTED:
                continue
            if member.flag_bits & 1:
                encrypted_members += 1
                continue
            try:
                columns = safe_member_header(zf, member)
            except (BadZipFile, OSError, RuntimeError, ValueError, UnicodeError, csv.Error):
                skipped_headers += 1
                continue
            if not columns:
                continue
            roles = classify(columns, member.filename)
            if not roles:
                continue
            found = {col.strip().lower() for col in columns}
            candidates.append({
                "archive_member": member.filename,
                "uncompressed_bytes": member.file_size,
                "compressed_bytes": member.compress_size,
                "columns": columns,
                "encounter_key_candidates": sorted(found & ENCOUNTERS),
                "possible_roles": roles,
            })
    candidates.sort(key=lambda x: (-max(z["score"] for z in x["possible_roles"]), x["archive_member"]))
    return {
        "stage": "ZIP_SOURCE_INVENTORY_ONLY",
        "archive_filename": path.name,
        "archive_members_total": len(members),
        "archive_members_examined": len(selected),
        "member_types": dict(sorted(counted_ext.items())),
        "sum_uncompressed_bytes": sum(m.file_size for m in members),
        "sum_compressed_member_bytes": sum(m.compress_size for m in members),
        "encrypted_csv_tsv_members_skipped": encrypted_members,
        "unreadable_or_long_headers_n": skipped_headers,
        "candidate_count": len(candidates),
        "candidates_omitted_from_report": max(0, len(candidates) - max_results),
        "candidates": candidates[:max_results],
        "truncated_at_max_members": len(members) > max_members,
        "warnings": [
            "No ZIP members were extracted or stored. CSV/TSV headers only were read.",
            "The archive may contain source data unrelated to this study or older exports.",
            "Filename/schema matches do not verify that encounters link correctly.",
            "ZIP member names and field names can be sensitive; review this report locally before sharing.",
            "Archive totals refer to ZIP member sizes, not estimated local disk requirements.",
            "Parquet or nested ZIP members are listed by type but not opened for schema inspection.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True, help="Approved local TriNetX ZIP path")
    p.add_argument("--max-members", type=int, default=2000)
    p.add_argument("--max-results", type=int, default=150)
    p.add_argument("--output", type=Path,
                   default=ROOT / "results/phase1/zip_source_inventory.json")
    args = p.parse_args()
    report = inspect_zip(args.zip, args.max_members, args.max_results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("Local metadata-only report:", args.output)
    print("ZIP members:", report["archive_members_total"])
    print("Schema candidates:", report["candidate_count"])
    print("Extensions:", report["member_types"])
    print("No patient records extracted. Inspect report before sharing.")


if __name__ == "__main__":
    main()
