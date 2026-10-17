#!/usr/bin/env python3
"""Step 39: local clinical worksheet for Research Network encounter-type codes.

Reads only a bounded encounter prefix and reference terminology CSV.
Raw type codes/descriptions and prefix per-code counts remain in a local,
gitignored worksheet. The review ZIP contains only aggregate status,
NO source codes, descriptions, patient IDs, or individual clinical rows.
Clinical encounter semantics remain UNVALIDATED.
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
from collections import Counter, defaultdict
from pathlib import Path

# Support both python scripts/step39_....py and pytest package imports.
if __package__:
    from .step38_encounter_type_terminology import (
        PHASE1, STEP36, STEP37, category_from_text, member_paths,
        normalize_type, read_encounter_types, secure_directory,
        save_private_json,
    )
else:
    from step38_encounter_type_terminology import (
        PHASE1, STEP36, STEP37, category_from_text, member_paths,
        normalize_type, read_encounter_types, secure_directory,
        save_private_json,
    )

STEP38 = PHASE1 / "step38_encounter_type_terminology.json"
WORKSHEET = "step39_encounter_type_clinical_review_LOCAL_ONLY.csv"
REPORT = "step39_encounter_type_review_status.json"
BUNDLE = "step39_encounter_type_review_status_UPLOAD_ONLY.zip"
HEADER = [
    "encounter_type_code", "reference_description", "reference_path",
    "prefix_record_count_NOT_PREVALENCE", "lexical_candidate_NOT_APPROVED",
    "clinician_decision_LEAVE_BLANK", "reviewer_notes_LEAVE_BLANK",
]


def read_reference(archive, member, wanted, maximum):
    """Materialize ONLY the few matching Encounter Type reference records."""
    matched = defaultdict(set)
    seen = 0
    encounter_reference_n = 0
    with archive.open(member) as raw, io.TextIOWrapper(
        raw, encoding="utf-8-sig", newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        required = {"code_system", "code", "code_description", "path"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Missing required terminology headers")
        for row in reader:
            if seen >= maximum:
                raise ValueError("Reference row bound reached: cannot claim complete mapping")
            seen += 1
            if normalize_type(row["code_system"]).replace("_", " ") != "ENCOUNTER TYPE":
                continue
            encounter_reference_n += 1
            code = normalize_type(row["code"])
            if code in wanted:
                matched[code].add(((row.get("code_description") or "").strip(), (row.get("path") or "").strip()))
    return matched, seen, encounter_reference_n


def private_write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".step39csv_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HEADER)
            writer.writeheader()
            writer.writerows(rows)
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def private_zip(path, report):
    fd, temp = tempfile.mkstemp(prefix=".step39zip_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as output, zipfile.ZipFile(
            output, "w", compression=zipfile.ZIP_DEFLATED
        ) as z:
            z.write(report, arcname=REPORT)
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run(archive_path, step36_path=STEP36, step37_path=STEP37,
        step38_path=STEP38, output_dir=PHASE1,
        maximum_encounters=50000, maximum_reference=3000000):
    if not 1 <= maximum_encounters <= 200000:
        raise ValueError("maximum encounters must be 1..200000")
    if not 1 <= maximum_reference <= 3000000:
        raise ValueError("maximum terminology rows must be 1..3000000")
    dest = secure_directory(output_dir)
    workbook = dest / WORKSHEET
    report_path = dest / REPORT
    bundle_path = dest / BUNDLE
    if archive_path.expanduser().resolve() in (
        workbook.resolve(), report_path.resolve(), bundle_path.resolve()
    ):
        raise ValueError("Input ZIP overlaps an output file")

    b36, b37, b38 = (p.read_bytes() for p in (step36_path, step37_path, step38_path))
    p36, p37, p38 = (json.loads(blob) for blob in (b36, b37, b38))
    if p36.get("stage") != "STEP36_RESEARCH_METADATA_PREFLIGHT" or not p36.get("schema_supports_attempted_encounter_linkage"):
        raise ValueError("Step36 readiness is missing")
    if p37.get("stage") != "STEP37_RESEARCH_ENCOUNTER_BOUNDED_PILOT" or p37.get("input_step36_sha256") != hashlib.sha256(b36).hexdigest():
        raise ValueError("Step37 provenance mismatch")
    if p38.get("stage") != "STEP38_ENCOUNTER_TYPE_REFERENCE_PILOT" or p38.get("input_step37_sha256") != hashlib.sha256(b37).hexdigest():
        raise ValueError("Step38 provenance mismatch")
    with zipfile.ZipFile(archive_path) as z:
        members = member_paths(z)
        expected_size = p36.get("files", {}).get("encounter.csv", {}).get("uncompressed_bytes")
        if expected_size != z.getinfo(members["encounter.csv"]).file_size:
            raise ValueError("Source encounter.csv differs from Step36 signature")
        counts, sampled_n = read_encounter_types(
            z, members["encounter.csv"], maximum_encounters
        )
        if sampled_n != p38.get("encounter_rows_examined"):
            raise ValueError("Step38 prefix length differs; use matching bounded sample")
        references, reference_n, vocab_n = read_reference(
            z, members["standardized_terminology.csv"], set(counts),
            maximum_reference
        )
    if reference_n != p38.get("terminology_rows_examined"):
        raise ValueError("Step38 reference scan length differs")
    if vocab_n != p38.get("encounter_type_reference_rows_found"):
        raise ValueError("Step38 encounter terminology row count differs")
    if len(counts) != p38.get("distinct_encounter_type_values_in_prefix"):
        raise ValueError("Step38 number of encounter types differs")
    if set(counts) != set(references):
        raise ValueError("Not all observed codes have reference definitions; abort worksheet")

    worksheet_rows = []
    has_multiple_descriptions = 0
    unresolved = 0
    for code in sorted(counts):
        entries = references[code]
        if len(entries) > 1:
            has_multiple_descriptions += 1
        classifications = set()
        for description, path in sorted(entries):
            category = category_from_text(description + " " + path)
            classifications.add(category)
            worksheet_rows.append({
                "encounter_type_code": code,
                "reference_description": description,
                "reference_path": path,
                "prefix_record_count_NOT_PREVALENCE": counts[code],
                "lexical_candidate_NOT_APPROVED": category,
                "clinician_decision_LEAVE_BLANK": "",
                "reviewer_notes_LEAVE_BLANK": "",
            })
        if classifications != {"inpatient_candidate"}:
            unresolved += 1
    summary = {
        "stage": "STEP39_PRIVATE_CLINICAL_CODEBOOK_REVIEW",
        "step38_sha256": hashlib.sha256(b38).hexdigest(),
        "nonrandom_encounter_prefix_n": sampled_n,
        "reference_rows_scanned": reference_n,
        "total_encounter_type_reference_rows": vocab_n,
        "distinct_encounter_codes_with_reference": len(counts),
        "local_worksheet_reference_rows": len(worksheet_rows),
        "codes_with_multiple_reference_descriptions_n": has_multiple_descriptions,
        "code_definitions_other_than_unambiguous_inpatient_n": unresolved,
        "output_contains_raw_terminology_values": False,
        "output_contains_patient_or_encounter_identifiers": False,
        "local_worksheet_created_but_EXCLUDED_FROM_REVIEW_ZIP": True,
        "clinician_approval_obtained": False,
        "hospitalization_case_definition_approved": False,
        "ready_for_stroke_inpatient_cohort": False,
        "instruction": "Review local worksheet privately with study neurologist/data steward; determine status of all five codes before any full source scan.",
    }
    private_write_csv(workbook, worksheet_rows)
    save_private_json(report_path, summary)
    private_zip(bundle_path, report_path)
    print("Step39 local codebook review generated; clinical approval remains required.")
    print("Encounter codes requiring review:", len(counts))
    print("Local-only worksheet (do NOT upload):", workbook)
    print("Aggregate-only review ZIP:", bundle_path)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--step36-json", type=Path, default=STEP36)
    p.add_argument("--step37-json", type=Path, default=STEP37)
    p.add_argument("--step38-json", type=Path, default=STEP38)
    p.add_argument("--output-dir", type=Path, default=PHASE1)
    p.add_argument("--max-encounters", type=int, default=50000)
    p.add_argument("--max-reference-rows", type=int, default=3000000)
    a = p.parse_args()
    run(a.zip, a.step36_json, a.step37_json, a.step38_json,
        a.output_dir, a.max_encounters, a.max_reference_rows)


if __name__ == "__main__":
    main()
