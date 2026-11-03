#!/usr/bin/env python3
"""Step 40: validate manually reviewed encounter-type decisions, locally only.

Consumes the private Step39 worksheet and aggregate Step39 status already
inside gitignored results/phase1/. Does NOT read original TriNetX source ZIP,
does NOT classify encounters automatically, and does NOT grant approval.
Only an aggregate decision-readiness JSON and review ZIP are exported.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE1 = ROOT / "results" / "phase1"
WORKSHEET = PHASE1 / "step39_encounter_type_clinical_review_LOCAL_ONLY.csv"
STATUS39 = PHASE1 / "step39_encounter_type_review_status.json"
REPORT = "step40_encounter_type_review_validation.json"
REVIEW_ZIP = "step40_encounter_type_review_validation_REVIEW.zip"
REQUIRED_FIELDS = (
    "encounter_type_code", "reference_description", "reference_path",
    "prefix_record_count_NOT_PREVALENCE", "lexical_candidate_NOT_APPROVED",
    "clinician_decision_LEAVE_BLANK", "reviewer_notes_LEAVE_BLANK",
)
VALID_DECISIONS = {
    "inpatient", "emergency", "observation", "outpatient", "virtual",
    "other", "unknown",
}


def inside_private_phase1(path: Path) -> Path:
    allowed = ROOT.resolve() / "results" / "phase1"
    if PHASE1.resolve() != allowed:
        raise ValueError("results/phase1 cannot be a symlink outside the repo")
    resolved = path.expanduser().resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("All Step40 input and output paths must remain inside results/phase1/")
    return resolved


def check_worksheet(path: Path, prior: dict) -> dict:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REQUIRED_FIELDS:
            raise ValueError("Step39 worksheet has an unexpected header/column order")
        rows = list(reader)
    expected = prior.get("local_worksheet_reference_rows")
    if not isinstance(expected, int) or expected < 1 or len(rows) != expected:
        raise ValueError("Worksheet row count does not match Step39 status")
    code_count = prior.get("distinct_encounter_codes_with_reference")
    if not isinstance(code_count, int) or code_count < 1:
        raise ValueError("Step39 status lacks a valid distinct-code count")
    code_to_definition = set()
    code_names = set()
    total_prefix = 0
    pending = 0
    undecidable = 0
    has_inpatient = False
    for row in rows:
        code = (row["encounter_type_code"] or "").strip()
        description = (row["reference_description"] or "").strip()
        path_value = (row["reference_path"] or "").strip()
        if not code or not description:
            raise ValueError("Worksheet has an empty encounter code or reference description")
        definition = (code, description, path_value)
        if definition in code_to_definition:
            raise ValueError("Duplicate code-definition row")
        code_to_definition.add(definition)
        code_names.add(code)
        count_text = (row["prefix_record_count_NOT_PREVALENCE"] or "").strip()
        if not count_text.isdecimal():
            raise ValueError("Invalid private prefix count")
        total_prefix += int(count_text)
        decision = (row["clinician_decision_LEAVE_BLANK"] or "").strip().lower()
        if not decision:
            pending += 1
        elif decision not in VALID_DECISIONS:
            raise ValueError("Invalid decision; see valid categories in Step40 documentation")
        elif decision == "unknown":
            undecidable += 1
        elif decision == "inpatient":
            has_inpatient = True
    if len(code_names) != code_count:
        raise ValueError("Distinct type-code count does not match Step39 status")
    if total_prefix != prior.get("nonrandom_encounter_prefix_n"):
        raise ValueError("Worksheet aggregate prefix count does not match Step39 status")
    if prior.get("stage") != "STEP39_PRIVATE_CLINICAL_CODEBOOK_REVIEW":
        raise ValueError("Wrong source Step39 stage")
    if prior.get("local_worksheet_created_but_EXCLUDED_FROM_REVIEW_ZIP") is not True:
        raise ValueError("Unexpected Step39 worksheet provenance")
    return {
        "codebook_rows_checked": len(rows),
        "all_codes_have_a_nonblank_decision": pending == 0,
        "any_decision_is_unknown": undecidable > 0,
        "any_code_was_classified_as_inpatient": has_inpatient,
        "clinical_review_complete_for_next_discussion": pending == 0 and undecidable == 0,
    }


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".step40_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def atomic_write_zip(path: Path, report: Path) -> None:
    fd, temp = tempfile.mkstemp(prefix=".step40zip_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream, zipfile.ZipFile(
            stream, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.write(report, arcname=REPORT)
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run(worksheet: Path = WORKSHEET, step39_json: Path = STATUS39,
        output_dir: Path = PHASE1) -> dict:
    input_worksheet = inside_private_phase1(worksheet)
    input_status = inside_private_phase1(step39_json)
    out = inside_private_phase1(output_dir)
    report, bundle = out / REPORT, out / REVIEW_ZIP
    if len({input_worksheet, input_status, report, bundle}) != 4:
        raise ValueError("Input files and output files must all have distinct paths")
    prior_blob = input_status.read_bytes()
    prior = json.loads(prior_blob)
    summary = check_worksheet(input_worksheet, prior)
    payload = {
        "stage": "STEP40_ENCOUNTER_TYPE_MANUAL_REVIEW_VALIDATION",
        "step39_status_sha256": hashlib.sha256(prior_blob).hexdigest(),
        **summary,
        "raw_encounter_type_codes_or_descriptions_exported": False,
        "patient_encounter_source_identifiers_exported": False,
        "individual_code_decisions_or_reviewer_notes_exported": False,
        "inpatient_definitions_clinically_approved": False,
        "provenance_and_encounter_join_scope_approved": False,
        "ready_for_full_linked_stroke_cohort_extraction": False,
        "next_action": (
            "Obtain and document explicit clinical/data-steward review of the five private codes, "
            "then validate encounter semantics, source_id and cohort capture before any full extraction."
        ),
    }
    atomic_write_json(report, payload)
    atomic_write_zip(bundle, report)
    print("Step40 local worksheet validation completed.")
    print("All code rows have decisions:", summary["all_codes_have_a_nonblank_decision"])
    print("Review report:", report)
    print("Review ZIP:", bundle)
    print("No clinical approval or full-cohort authorization inferred.")
    return payload


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worksheet", type=Path, default=WORKSHEET)
    p.add_argument("--step39-json", type=Path, default=STATUS39)
    p.add_argument("--output-dir", type=Path, default=PHASE1)
    a = p.parse_args()
    run(a.worksheet, a.step39_json, a.output_dir)


if __name__ == "__main__":
    main()
