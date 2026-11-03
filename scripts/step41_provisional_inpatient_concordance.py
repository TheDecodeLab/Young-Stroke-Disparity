#!/usr/bin/env python3
"""Step 41: nonrepresentative IMP-candidate encounter/event concordance pilot.

Technical linkage check ONLY. Reads <=50k prefix rows from encounter,
diagnosis, procedure, plus existing local private Step39 worksheet.
NO full clinical scan, no patient-level output, no clinical approval.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import os
import stat
import tempfile
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

if __package__:
    from .step37_research_encounter_pilot import (
        PHASE1, STEP36, REPORT_NAME as STEP37_NAME,
        CPT14, FIELDS, TABLES, find_members, preflight_match, private_count,
    )
else:
    from step37_research_encounter_pilot import (
        PHASE1, STEP36, REPORT_NAME as STEP37_NAME,
        CPT14, FIELDS, TABLES, find_members, preflight_match, private_count,
    )

ROOT = Path(__file__).resolve().parents[1]
STEP37 = PHASE1 / STEP37_NAME
STEP39_WORKSHEET = PHASE1 / "step39_encounter_type_clinical_review_LOCAL_ONLY.csv"
REPORT = "step41_imp_encounter_concordance_pilot.json"
REVIEW_ZIP = "step41_imp_encounter_concordance_pilot_REVIEW.zip"
N_DEFAULT = 50000


def parse_date(raw):
    """Known day-unambiguous formats only; no imputation or locale guessing."""
    val = (raw or "").strip().split("T", 1)[0].split(" ", 1)[0]
    try:
        if len(val) == 8 and val.isdecimal():
            return date(int(val[:4]), int(val[4:6]), int(val[6:8]))
        if len(val) == 10 and val[4] == val[7] == "-":
            return date.fromisoformat(val)
        if len(val) == 10 and val[4] == val[7] == "/":
            return date(int(val[:4]), int(val[5:7]), int(val[8:10]))
    except ValueError:
        return None
    return None


def private_root(path):
    allowed = ROOT.resolve() / "results" / "phase1"
    if PHASE1.resolve() != allowed:
        raise ValueError("results/phase1 cannot be a symlink escape")
    resolved = path.expanduser().resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("Paths must stay inside cloned repo results/phase1/")
    return resolved


def candidate_inpatient_codes(path):
    """Provisional lexical candidate from local dictionary; not reviewer approval."""
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        required = {"encounter_type_code", "reference_description",
                    "lexical_candidate_NOT_APPROVED"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Step39 worksheet missing expected fields")
        matches = {
            (row.get("encounter_type_code") or "").strip().upper()
            for row in reader
            if (row.get("lexical_candidate_NOT_APPROVED") or "").strip()
            == "inpatient_candidate"
            and "inpatient encounter" in (row.get("reference_description") or "").lower()
        }
    matches.discard("")
    if not matches or len(matches) > 3:
        raise ValueError("No unambiguous provisional inpatient candidate in local codebook")
    return matches


def prefix_rows(archive, member, table, n):
    with archive.open(member) as binary, io.TextIOWrapper(
        binary, encoding="utf-8-sig", newline=""
    ) as fh:
        reader = csv.DictReader(fh)
        missing = FIELDS[table] - set(reader.fieldnames or ())
        if missing:
            raise ValueError("Missing required headers for " + table + ": " + ", ".join(sorted(missing)))
        yield from itertools.islice(reader, n)


def analyze(archive, members, inpatient_codes, limit):
    imp = {}
    read_counts = {}
    dup_count = conflicting_patients = invalid_index_date = 0
    rows = 0
    for r in prefix_rows(archive, members["encounter.csv"], "encounter.csv", limit):
        rows += 1
        if (r.get("type") or "").strip().upper() not in inpatient_codes:
            continue
        eid = (r.get("encounter_id") or "").strip()
        pid = (r.get("patient_id") or "").strip()
        if not eid or not pid:
            continue
        start = parse_date(r.get("start_date"))
        if start is None:
            invalid_index_date += 1
        if eid in imp:
            dup_count += 1
            if imp[eid][0] != pid:
                conflicting_patients += 1
        else:
            imp[eid] = (pid, start)
    read_counts["encounter.csv"] = rows
    if conflicting_patients:
        raise ValueError("Conflicting patients on sampled inpatient encounter IDs")
    signals = {key: {"i63": False, "cpt14": False, "same_encounter_cpt14_pm7": False}
               for key in imp}
    diag_row_matches = 0
    image_row_matches = 0
    mismatched_patient = 0
    unknown_event_date = 0
    linked_diag_events = 0
    linked_procedure_events = 0
    for table in ("diagnosis.csv", "procedure.csv"):
        rows = 0
        for r in prefix_rows(archive, members[table], table, limit):
            rows += 1
            eid = (r.get("encounter_id") or "").strip()
            if eid not in imp:
                continue
            pid, start = imp[eid]
            if (r.get("patient_id") or "").strip() != pid:
                mismatched_patient += 1
                continue
            if table == "diagnosis.csv":
                linked_diag_events += 1
                if (r.get("code_system") or "").strip().upper() == "ICD-10-CM" and (
                    (r.get("code") or "").strip().upper().startswith("I63.")
                    or (r.get("code") or "").strip().upper() == "I63"
                ):
                    signals[eid]["i63"] = True
                    diag_row_matches += 1
            else:
                linked_procedure_events += 1
                if ((r.get("code_system") or "").strip().upper() == "CPT"
                        and (r.get("code") or "").strip() in CPT14):
                    image_row_matches += 1
                    signals[eid]["cpt14"] = True
                    event_day = parse_date(r.get("date"))
                    if start is None or event_day is None:
                        unknown_event_date += 1
                    elif abs((event_day - start).days) <= 7:
                        signals[eid]["same_encounter_cpt14_pm7"] = True
        read_counts[table] = rows
    combos = Counter()
    for key, flags in signals.items():
        _, day = imp[key]
        year = "2018_2019" if day and day.year in (2018, 2019) else "other_or_missing_year"
        for name, flag in flags.items():
            if flag:
                combos[name] += 1
                if year == "2018_2019":
                    combos[name + "_2018_2019"] += 1
        if flags["i63"] and flags["same_encounter_cpt14_pm7"]:
            combos["both_I63_and_CPT14_in_same_sampled_encounter"] += 1
    sums = {
        "sampled_encounter_rows": read_counts["encounter.csv"],
        "sampled_diagnosis_rows": read_counts["diagnosis.csv"],
        "sampled_procedure_rows": read_counts["procedure.csv"],
        "distinct_candidate_inpatient_encounter_ids_n": private_count(len(imp)),
        "duplicate_inpatient_encounter_id_rows_n": private_count(dup_count),
        "invalid_inpatient_start_dates_n": private_count(invalid_index_date),
        "linked_diagnosis_event_rows_with_matching_patient_n": private_count(linked_diag_events),
        "linked_procedure_event_rows_with_matching_patient_n": private_count(linked_procedure_events),
        "matched_prefix_events_with_different_patient_id_n": private_count(mismatched_patient),
        "I63_diagnosis_event_rows_n": private_count(diag_row_matches),
        "CPT14_procedure_event_rows_n": private_count(image_row_matches),
        "CPT14_rows_with_missing_date_or_start_n": private_count(unknown_event_date),
    }
    sums.update({key + "_encounters_n": private_count(value) for key, value in sorted(combos.items())})
    return sums


def atomic_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".step41_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(content, file, sort_keys=True, indent=2)
            file.write("\n")
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def atomic_zip(path, report):
    fd, temp = tempfile.mkstemp(prefix=".step41zip_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as file, zipfile.ZipFile(
            file, "w", compression=zipfile.ZIP_DEFLATED
        ) as z:
            z.write(report, arcname=REPORT)
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run(source, step36=STEP36, step37=STEP37,
        worksheet=STEP39_WORKSHEET, output_dir=PHASE1,
        max_rows=50000):
    if not 1 <= max_rows <= 200000:
        raise ValueError("--max-rows-per-table must be 1..200000")
    output = private_root(output_dir)
    p36_path, p37_path, wpath = (private_root(x) for x in (step36, step37, worksheet))
    if any(source.expanduser().resolve() == path for path in
           (output / REPORT, output / REVIEW_ZIP)):
        raise ValueError("Source ZIP would be overwritten")
    b36, b37 = p36_path.read_bytes(), p37_path.read_bytes()
    p36, p37 = json.loads(b36), json.loads(b37)
    if (p37.get("stage") != "STEP37_RESEARCH_ENCOUNTER_BOUNDED_PILOT"
            or p37.get("input_step36_sha256") != hashlib.sha256(b36).hexdigest()):
        raise ValueError("Step37 does not match Step36 source report")
    if max_rows != p37.get("max_rows_per_clinical_table"):
        raise ValueError("Step41 max rows must match Step37 pilot's sample prefix length")
    provisional_codes = candidate_inpatient_codes(wpath)
    with zipfile.ZipFile(source) as archive:
        members = find_members(archive)
        preflight_match(archive, members, p36)
        sums = analyze(archive, members, provisional_codes, max_rows)
    payload = {
        "stage": "STEP41_PROVISIONAL_INPATIENT_ENCOUNTER_CONCORDANCE_PILOT",
        "step36_sha256": hashlib.sha256(b36).hexdigest(),
        "step37_sha256": hashlib.sha256(b37).hexdigest(),
        "max_rows_per_clinical_table": max_rows,
        "sampling": "independent_first_N_file_prefixes_NOT_RANDOM",
        "inpatient_candidate_codes_inferred_from_private_dictionary_not_exported": True,
        "candidate_definition_clinically_approved": False,
        "patient_or_encounter_identifiers_exported": False,
        "raw_type_codes_or_descriptions_exported": False,
        "candidate_encounter_prefix_selected_without_imaging_requirement": True,
        "eligible_young_stroke_population_validated": False,
        "inpatient_episode_validated": False,
        "imaging_utilization_validated": False,
        "ready_for_disparity_model": False,
        "technical_prefix_counts": sums,
        "limitations": [
            "The three prefixes may be sorted differently and are not representative.",
            "Unobserved diagnosis or procedure rows cannot be treated as absent care.",
            "Only selected CPT imaging codes are audited; full MRI/CTA/MRA capture is not validated.",
            "Candidate inpatient label does not establish principal inpatient stroke admission.",
            "Year buckets do not prove day-level clinical timing accuracy.",
            "Aggregate counts may be disclosure sensitive; data steward review before sharing.",
        ],
    }
    report_path, zip_path = output / REPORT, output / REVIEW_ZIP
    atomic_json(report_path, payload)
    atomic_zip(zip_path, report_path)
    print("Step41 technical concordance pilot completed (NOT population inference).")
    print("Aggregate report:", report_path)
    print("Review ZIP:", zip_path)
    return payload


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--step36-json", type=Path, default=STEP36)
    p.add_argument("--step37-json", type=Path, default=STEP37)
    p.add_argument("--worksheet", type=Path, default=STEP39_WORKSHEET)
    p.add_argument("--output-dir", type=Path, default=PHASE1)
    p.add_argument("--max-rows-per-table", type=int, default=N_DEFAULT)
    a = p.parse_args()
    run(a.zip, a.step36_json, a.step37_json, a.worksheet,
        a.output_dir, a.max_rows_per_table)


if __name__ == "__main__":
    main()
