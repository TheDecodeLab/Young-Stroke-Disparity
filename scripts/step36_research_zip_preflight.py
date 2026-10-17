#!/usr/bin/env python3
"""Step 36: metadata-only preflight of a local TriNetX Research Network ZIP.

Reads ZIP central directory, only first line (header) of selected CSV members,
and three small export metadata CSV files. No patient-level rows or source
identifiers are included in output. No unzip/extract and no clinical table scan.
The local operator should review even the aggregate JSON before sharing it.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
import stat
import zipfile
from pathlib import Path

CLINICAL_TABLES = (
    "patient.csv", "patient_cohort.csv", "encounter.csv", "diagnosis.csv", "procedure.csv"
)
META_TABLES = ("manifest.csv", "dataset_details.csv", "cohort_details.csv")
REQUIRED = {
    "patient.csv": {"patient_id", "sex", "race", "ethnicity", "year_of_birth"},
    "encounter.csv": {"encounter_id", "patient_id", "start_date", "end_date", "type"},
    "diagnosis.csv": {"patient_id", "encounter_id", "code_system", "code", "date", "principal_diagnosis_indicator"},
    "procedure.csv": {"patient_id", "encounter_id", "code_system", "code", "date"},
}

def find_csv_files(archive: zipfile.ZipFile) -> tuple[dict[str, str], list[str]]:
    mapping = {}
    warnings = []
    for name in archive.namelist():
        if name.endswith("/"):
            continue
        basename = name.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if basename in CLINICAL_TABLES + META_TABLES:
            if basename in mapping:
                warnings.append(f"duplicate archive member basename: {basename}")
            else:
                mapping[basename] = name
    return mapping, warnings

def csv_header(archive: zipfile.ZipFile, member: str) -> list[str]:
    with archive.open(member) as raw:
        # io.BufferedReader.readline retrieves only first logical CSV line;
        # TriNetX column names are plain text and contain no quoted newlines.
        first = raw.readline(128 * 1024)
    if not first.endswith((b"\n", b"\r")):
        raise ValueError(f"Header exceeds read limit or is incomplete: {member}")
    return next(csv.reader([first.decode("utf-8-sig").strip("\r\n")]))

def small_csv(archive: zipfile.ZipFile, member: str, max_uncompressed: int = 2_000_000) -> list[dict]:
    info = archive.getinfo(member)
    if info.file_size > max_uncompressed:
        raise ValueError(f"Metadata member unexpectedly large: {member}")
    with archive.open(member) as f:
        blob = f.read(max_uncompressed + 1)
    if len(blob) > max_uncompressed:
        raise ValueError(f"Metadata member exceeds size limit: {member}")
    return list(csv.DictReader(io.StringIO(blob.decode("utf-8-sig"))))

def positive_int(value):
    try:
        n = int(value)
        return n if n >= 0 else None
    except (TypeError, ValueError):
        return None

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", dest="archive_path", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--output-zip", type=Path, help="Optional metadata-only ZIP for review")
    args = ap.parse_args()
    warnings = []
    result = {"stage": "STEP36_RESEARCH_METADATA_PREFLIGHT", "clinical_rows_read": 0,
              "full_clinical_tables_scanned": False, "encounter_linkage_verified": False,
              "inpatient_classification_verified": False,
              "imaging_capture_verified": False, "files": {}, "export_metadata": {},
              "relevant_manifest_counts": {}, "warnings": warnings}
    with zipfile.ZipFile(args.archive_path, "r") as z:
        mapping, member_warnings = find_csv_files(z)
        warnings.extend(member_warnings)
        for basename in CLINICAL_TABLES:
            member = mapping.get(basename)
            if not member:
                warnings.append("missing required table: " + basename)
                continue
            headers = csv_header(z, member)
            missing_fields = sorted(REQUIRED.get(basename, set()) - set(headers))
            if missing_fields:
                warnings.append(f"missing expected {basename} fields: {', '.join(missing_fields)}")
            result["files"][basename] = {
                "present": True, "headers": headers,
                "uncompressed_bytes": z.getinfo(member).file_size,
                "missing_expected_fields": missing_fields,
            }
        for basename in META_TABLES:
            member = mapping.get(basename)
            if not member:
                warnings.append("missing metadata: " + basename)
                continue
            rows = small_csv(z, member)
            if basename == "manifest.csv":
                for row in rows:
                    key = (row.get("file") or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
                    if key in CLINICAL_TABLES:
                        result["relevant_manifest_counts"][key] = {
                            "row_count": positive_int(row.get("row_count")),
                            "unique_patient_count": positive_int(row.get("unique_patient_count")),
                        }
            elif basename == "dataset_details.csv":
                for row in rows[:1]:
                    result["export_metadata"] = {
                        "network_name": row.get("network_name"),
                        "date_created": row.get("date_created"),
                        "total_number_unique_patients": positive_int(row.get("total_number_unique_patients")),
                        "total_number_HCOs": positive_int(row.get("total_number_HCOs")),
                    }
            elif basename == "cohort_details.csv":
                result["cohort_metadata"] = [
                    {"cohort_name": r.get("cohort_name"),
                     "cohort_number": r.get("cohort_number"),
                     "total_patient_records": positive_int(r.get("total_patient_records"))}
                    for r in rows[:30]
                ]
    result["schema_supports_attempted_encounter_linkage"] = not any(
        w.startswith("duplicate archive member basename:") for w in warnings
    ) and all(
        name in result["files"] and not result["files"][name]["missing_expected_fields"]
        for name in ("patient.csv", "encounter.csv", "diagnosis.csv", "procedure.csv")
    )
    # Schema support does NOT establish event linkage, clinical completeness or valid inpatient labels.
    # Prevent accidental writing of review outputs into tracked repository paths.
    root = Path(__file__).resolve().parents[1]
    allowed = root / "results"
    paths = [args.output, *([args.output_zip] if args.output_zip else [])]
    for path in paths:
        resolved = path.expanduser().resolve()
        if root in resolved.parents and resolved != allowed and allowed not in resolved.parents:
            raise ValueError("Output inside repository must be under ignored results/")
    if args.output_zip and args.output_zip.resolve() == args.output.resolve():
        raise ValueError("--output and --output-zip must differ")
    # Preserve permissions on any existing parent directory.
    # Private workspace access is the local data steward's responsibility.
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as dst:
        json.dump(result, dst, indent=2, sort_keys=True)
        dst.write("\n")
    os.chmod(args.output, stat.S_IRUSR | stat.S_IWUSR)
    if args.output_zip:
        args.output_zip.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        zip_fd = os.open(args.output_zip, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(zip_fd, "wb") as dest, zipfile.ZipFile(
            dest, "w", compression=zipfile.ZIP_DEFLATED
        ) as bundle:
            bundle.write(args.output, arcname="step36_research_metadata_preflight.json")
        os.chmod(args.output_zip, stat.S_IRUSR | stat.S_IWUSR)
        print("Metadata-only review ZIP:", args.output_zip)
    print("Preflight completed; metadata-only output:", args.output)
    print("Schema supports potential linkage:", result["schema_supports_attempted_encounter_linkage"])
    print("Warnings:", len(warnings))
    print("Clinical records read: 0. Encounter linkage/inpatient validity NOT tested.")

if __name__ == "__main__":
    main()