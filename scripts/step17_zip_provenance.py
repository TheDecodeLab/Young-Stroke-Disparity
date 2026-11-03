"""Step 17: inspect tiny provenance members of original TriNetX ZIP.

Reads only bounded aggregate dataset metadata: manifest.csv,
cohort_details.csv, dataset_details.csv and readme.txt. Never opens
patient, diagnosis, procedure or patient_cohort rows. No entire ZIP
extraction. Local report contains cohort labels and metadata, so review
before sharing. This does NOT validate diagnoses or encounters.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("manifest.csv", "cohort_details.csv", "dataset_details.csv", "readme.txt")
MAX_MEMBER_BYTES = 1_048_576
MAX_CSV_ROWS = 500
PREVIEW = {"diagnosis.csv", "procedure.csv", "patient.csv", "patient_cohort.csv"}


def number(value: str | None) -> int | None:
    """Parse aggregate numeric metadata only."""
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text.isdigit():
        return None
    return int(text)


def read_bounded(zf: ZipFile, name: str, limit: int) -> tuple[bytes | None, str]:
    if name not in zf.namelist():
        return None, "not_found"
    info = zf.getinfo(name)
    if info.file_size > limit:
        return None, "too_large_for_metadata_audit"
    with zf.open(name) as handle:
        payload = handle.read(limit + 1)
    if len(payload) > limit:
        return None, "too_large_for_metadata_audit"
    return payload, "read"


def csv_dicts(payload: bytes) -> list[dict[str, str]]:
    text = payload.decode("utf-8-sig", errors="replace")
    iterator = csv.DictReader(io.StringIO(text))
    result = []
    for i, row in enumerate(iterator):
        if i >= MAX_CSV_ROWS:
            raise ValueError("Metadata CSV exceeds bounded row limit")
        result.append({k: (v or "").strip() for k, v in row.items() if k is not None})
    return result


def audit_zip(path: Path, limit: int = MAX_MEMBER_BYTES) -> dict:
    """Read tiny metadata, never clinical rows."""
    if limit < 1 or limit > MAX_MEMBER_BYTES:
        raise ValueError(f"limit must be between 1 and {MAX_MEMBER_BYTES}")
    if not path.is_file():
        raise FileNotFoundError(path)
    with ZipFile(path, "r") as zf:
        names = set(zf.namelist())
        results = {}
        for name in SOURCES:
            payload, status = read_bounded(zf, name, limit)
            entry = {"status": status}
            if payload is None:
                results[name] = entry
                continue
            if name == "readme.txt":
                text = payload.decode("utf-8-sig", errors="replace")
                search = text.lower()
                entry.update({
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                    "line_count": len(text.splitlines()),
                    "mentions_encounter": "encounter" in search,
                    "mentions_visit": "visit" in search,
                    "mentions_admission": "admission" in search,
                    "mentions_claims": "claims" in search,
                    "mentions_license": "license" in search or "licence" in search,
                })
                # No raw README text, institutional names, or paths.
            else:
                rows = csv_dicts(payload)
                entry["metadata_records_n"] = len(rows)
                if name == "manifest.csv":
                    data = []
                    for row in rows:
                        file_name = row.get("file", "")
                        if file_name in PREVIEW:
                            data.append({
                                "source": file_name,
                                "declared_rows": number(row.get("row_count")),
                                "declared_unique_patients": number(row.get("unique_patient_count")),
                                "archive_member_present": file_name in names,
                                "bytes_uncompressed": zf.getinfo(file_name).file_size
                                if file_name in names else None,
                            })
                    entry["relevant_source_statistics"] = data
                    entry["source_rows_have_numeric_counts"] = all(
                        x["declared_rows"] is not None for x in data
                    ) if data else False
                elif name == "cohort_details.csv":
                    # Names are descriptions of cohort filters, not patient rows.
                    # Review locally; cohort label alone does not verify eligibility.
                    entry["cohort_descriptions"] = [
                        {
                            "cohort_name": row.get("cohort_name", "")[:120],
                            "cohort_number": row.get("cohort_number", "")[:30],
                            "total_patient_records": number(row.get("total_patient_records")),
                        } for row in rows
                    ]
                elif name == "dataset_details.csv":
                    entry["dataset_aggregates"] = [
                        {
                            "total_number_unique_patients":
                                number(row.get("total_number_unique_patients")),
                            "total_number_HCOs": number(row.get("total_number_HCOs")),
                            "date_created": row.get("date_created", "")[:40],
                            "network_name_withheld": True,
                        } for row in rows
                    ]
            results[name] = entry
        return {
            "stage": "AGGREGATE_SOURCE_PROVENANCE_ONLY",
            "archive_member_count": len(names),
            "metadata": results,
            "original_clinical_rows_read": 0,
            "ready_for_encounter_level_reconstruction": False,
            "caveats": [
                "Cohort labels and manifest counts are metadata, not proof of eligible stroke admissions.",
                "No patient, diagnosis, procedure or patient_cohort records were inspected.",
                "The source headers contain no validated encounter/admission identifier.",
                "Any full reconstruction must define principal stroke index independent of MRI/CTA/MRA.",
                "Check local data-use approval and avoid committing patient-level outputs.",
            ],
        }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--output", type=Path,
                   default=ROOT / "results/phase1/zip_provenance.json")
    args = p.parse_args()
    out = audit_zip(args.zip)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Aggregate-only provenance report:", args.output)
    for key, value in out["metadata"].items():
        print(key, value["status"])
    print("No clinical rows accessed. Inspect cohort labels before sharing.")


if __name__ == "__main__":
    main()
