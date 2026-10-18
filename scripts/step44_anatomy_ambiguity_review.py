#!/usr/bin/env python3
"""Step44: inspect anatomy ambiguity in PRIVATE Step43 terminology worksheets.

Reference only. No source TriNetX ZIP, patient, encounter, or procedure
records accessed. This does not approve or exclude imaging codes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import stat
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

if __package__:
    from .step43_neuroimaging_review_triage import (
        PHASE1, FULL as STEP43_FULL, REPORT as STEP43_REPORT,
        FIELDS as STEP43_FIELDS, private_path, safe_spreadsheet_cell,
    )
else:
    from step43_neuroimaging_review_triage import (
        PHASE1, FULL as STEP43_FULL, REPORT as STEP43_REPORT,
        FIELDS as STEP43_FIELDS, private_path, safe_spreadsheet_cell,
    )

FULL = "step44_anatomy_ambiguity_full_LOCAL_ONLY.csv"
FIRST = "step44_anatomy_ambiguity_review_first_LOCAL_ONLY.csv"
REPORT = "step44_anatomy_ambiguity_status.json"
REVIEW = "step44_anatomy_ambiguity_status_REVIEW.zip"
REVIEW_FIELDS = STEP43_FIELDS + ("anatomy_ambiguity_origin_NOT_APPROVED",)
AMBIGUOUS = "AMBIGUOUS_HEAD_AND_NECK"
DESCRIPTION_SPECIFIC = {
    "MRI_BRAIN", "CT_HEAD", "CTA_HEAD", "CTA_NECK", "MRA_HEAD", "MRA_NECK",
}
SUBTYPES = (
    "description_specific_but_reference_path_mixed",
    "head_and_neck_mixed_in_description",
    "only_reference_path_indicates_anatomy",
    "other_description_disagreement",
)


def ambiguity_origin(row):
    """Technical priority only; never a clinical reclassification."""
    desc = (row.get("description_only_modality_anatomy_match") or "").strip()
    if desc in DESCRIPTION_SPECIFIC:
        return SUBTYPES[0]
    if desc == AMBIGUOUS:
        return SUBTYPES[1]
    if desc == "NONE":
        return SUBTYPES[2]
    return SUBTYPES[3]


def read_source(worksheet: Path, status_path: Path):
    blob = status_path.read_bytes()
    report = json.loads(blob)
    if (report.get("stage") != "STEP43_REFERENCE_CODEBOOK_REVIEW_TRIAGE"
            or report.get("clinical_event_rows_examined") != 0
            or report.get("all_candidate_rows_preserved_in_private_full_worksheet") is not True):
        raise ValueError("Step43 status does not document complete reference-only source")
    with worksheet.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != STEP43_FIELDS:
            raise ValueError("Unexpected Step43 full worksheet header")
        rows = list(reader)
    if len(rows) != report.get("source_candidate_rows"):
        raise ValueError("Step43 source candidate row count mismatch")
    if dict(Counter(r["candidate_category_NOT_VALIDATED"] for r in rows)) != report.get("full_candidate_category_counts"):
        raise ValueError("Step43 category totals mismatch")
    if dict(Counter(r["triage_bucket_NOT_CLINICALLY_VALIDATED"] for r in rows)) != report.get("triage_bucket_counts"):
        raise ValueError("Step43 tier totals mismatch")
    return rows, blob


def private_bytes(path: Path, contents: bytes):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".step44_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(contents)
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def csv_payload(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: safe_spreadsheet_cell(row.get(k, "")) for k in REVIEW_FIELDS})
    return stream.getvalue().encode("utf-8")


def private_zip(path, report_path):
    fd, temp = tempfile.mkstemp(prefix=".step44zip_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as out, zipfile.ZipFile(
            out, "w", compression=zipfile.ZIP_DEFLATED
        ) as z:
            z.write(report_path, arcname=REPORT)
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run(step43_csv=PHASE1 / STEP43_FULL,
        step43_json=PHASE1 / STEP43_REPORT,
        output_dir=PHASE1, per_origin=15, overwrite=False):
    if not 1 <= per_origin <= 50:
        raise ValueError("--review-per-origin must be 1..50")
    inp = private_path(step43_csv)
    status = private_path(step43_json)
    out = private_path(output_dir)
    dest = [out / name for name in (FULL, FIRST, REPORT, REVIEW)]
    if len(set([inp, status] + dest)) != 6:
        raise ValueError("Inputs must be distinct from all output files")
    if not overwrite and any(path.exists() for path in dest):
        raise FileExistsError(
            "Step44 outputs exist; preserve review edits or explicitly pass --overwrite"
        )

    rows, status_blob = read_source(inp, status)
    ambiguous = []
    for r in rows:
        if r["candidate_category_NOT_VALIDATED"] == AMBIGUOUS:
            item = dict(r)
            item["anatomy_ambiguity_origin_NOT_APPROVED"] = ambiguity_origin(r)
            ambiguous.append(item)
    subgroup_counts = Counter(r["anatomy_ambiguity_origin_NOT_APPROVED"] for r in ambiguous)
    if len(ambiguous) != sum(subgroup_counts.values()):
        raise ValueError("Ambiguity subgroup totals do not reconcile")
    by_origin = {s: [] for s in SUBTYPES}
    for item in ambiguous:
        by_origin[item["anatomy_ambiguity_origin_NOT_APPROVED"]].append(item)
    ambiguous.sort(key=lambda r: (
        SUBTYPES.index(r["anatomy_ambiguity_origin_NOT_APPROVED"]),
        r["code_system"], r["code"], r["code_description"],
    ))
    sample = []
    for group in SUBTYPES:
        sample.extend(by_origin[group][:per_origin])
    def small(n):
        return "suppressed_1_to_10" if 0 < n < 11 else n
    payload = {
        "stage": "STEP44_REFERENCE_ONLY_ANATOMY_AMBIGUITY_DIAGNOSTIC",
        "input_step43_status_sha256": hashlib.sha256(status_blob).hexdigest(),
        "clinical_event_rows_examined": 0,
        "source_candidates_n": len(rows),
        "original_ambiguous_candidates_n": len(ambiguous),
        "subtype_candidate_counts": {s: small(subgroup_counts[s]) for s in SUBTYPES},
        "review_first_rows_n": len(sample),
        "full_ambiguous_reference_rows_preserved": True,
        "no_automatic_code_reclassification_or_inclusion": True,
        "private_full_and_first_review_worksheets_created": True,
        "raw_codes_descriptions_and_review_notes_exported": False,
        "eligible_imaging_codebook_validated": False,
        "clinical_disparities_cohort_authorized": False,
        "notes": [
            "Description-only anatomy is compared with original description+path assignment.",
            "Descriptions can still be nonspecific, false-positive, ordered, or nonprocedure concepts.",
            "No row is excluded from the original Step43 full candidate worksheet.",
            "Even a description-specific ambiguous code requires clinical review.",
            "Local first-review worksheet is a small convenience subset, NOT a complete codebook.",
            "Do not share the local CSVs; check data-use/disclosure permissions for this aggregate ZIP.",
        ],
    }
    private_bytes(out / FULL, csv_payload(ambiguous))
    private_bytes(out / FIRST, csv_payload(sample))
    private_bytes(out / REPORT, (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode())
    private_zip(out / REVIEW, out / REPORT)
    print("Step44 private anatomy ambiguity review diagnostic complete.")
    print("Clinical event rows read: 0")
    print("Local-only full worksheet:", out / FULL)
    print("Local-only first-review worksheet:", out / FIRST)
    print("Aggregate review ZIP:", out / REVIEW)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step43-csv", type=Path, default=PHASE1 / STEP43_FULL)
    parser.add_argument("--step43-json", type=Path, default=PHASE1 / STEP43_REPORT)
    parser.add_argument("--output-dir", type=Path, default=PHASE1)
    parser.add_argument("--review-per-origin", type=int, default=15)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    run(args.step43_csv, args.step43_json, args.output_dir,
        args.review_per_origin, args.overwrite)


if __name__ == "__main__":
    main()
