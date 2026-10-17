#!/usr/bin/env python3
"""Step 37: bounded, local Research Network encounter feasibility PILOT.

Streams at most N *prefix* rows from each of encounter, diagnosis, procedure
in the local ZIP. No raw rows, IDs, dates, or source file paths are exported.
Prefix samples are NONRANDOM and cannot establish population join coverage,
imaging utilization, inpatient validity, or disparities.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import os
import re
import stat
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE1 = ROOT / "results" / "phase1"
STEP36 = PHASE1 / "step36_research_metadata_preflight.json"
REPORT_NAME = "step37_research_encounter_pilot.json"
ZIP_NAME = "step37_research_encounter_pilot_review.zip"
TABLES = ("encounter.csv", "diagnosis.csv", "procedure.csv")
FIELDS = {
    "encounter.csv": {"encounter_id", "patient_id", "start_date", "end_date", "type"},
    "diagnosis.csv": {
        "patient_id", "encounter_id", "code_system", "code", "date",
        "principal_diagnosis_indicator",
    },
    "procedure.csv": {
        "patient_id", "encounter_id", "code_system", "code", "date",
    },
}
CPT14 = {
    "70450", "70460", "70470", "70496", "70498", "70551", "70552",
    "70553", "70544", "70545", "70546", "70547", "70548", "70549",
}
REDACTED = "suppressed_1_to_10"


def private_count(number):
    """Suppress 1-10; zero and 11+ allowed in PRIVATE review material."""
    return REDACTED if 0 < number < 11 else number


def date_profile(raw):
    """Return (coarse date-shape category, year bucket, ambiguity flag).

    Never export literal source dates. The year is usable without resolving
    month/day order where the year is last, but episode-day matching is NOT.
    """
    import datetime
    value = (raw or "").strip()
    if not value:
        return "missing", "missing", False
    shape = "unrecognized"
    parts = None
    year = month = day = None
    ambiguous = False
    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:$|[ T])", value)
    if match:
        shape = "year_first_dash"
        year, month, day = map(int, match.groups())
    else:
        match = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})(?:$|[ T])", value)
        if match:
            shape = "year_first_slash"
            year, month, day = map(int, match.groups())
        else:
            match = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", value)
            if match:
                shape = "compact_yyyymmdd"
                year, month, day = map(int, match.groups())
            else:
                match = re.match(r"^(\d{1,2})/([0-9]{1,2})/(\d{4})(?:$|[ T])", value)
                if match:
                    shape = "year_last_slash"
                    first, second, year = map(int, match.groups())
                    # Either US month/day or day/month may be valid.
                    valid_us = valid_day_first = False
                    try:
                        datetime.date(year, first, second)
                        valid_us = True
                    except ValueError:
                        pass
                    try:
                        datetime.date(year, second, first)
                        valid_day_first = True
                    except ValueError:
                        pass
                    if not (valid_us or valid_day_first):
                        return shape, "unparseable", False
                    ambiguous = valid_us and valid_day_first and first != second
                    # Both valid interpretations have the same calendar year.
                    month, day = (first, second) if valid_us else (second, first)
                elif re.fullmatch(r"\d{10}|\d{13}", value):
                    return "unix_epoch_candidate_unverified", "unparseable", False
                else:
                    return "unrecognized", "unparseable", False
    try:
        datetime.date(year, month, day)
    except (ValueError, TypeError):
        return shape, "unparseable", ambiguous
    if year in (2018, 2019):
        bucket = "2018_2019"
    elif 2020 <= year <= 2025:
        bucket = "2020_2025"
    elif 1900 <= year <= 2017:
        bucket = "before_2018"
    else:
        bucket = "other_year"
    return shape, bucket, ambiguous


def coarse_year(raw):
    return date_profile(raw)[1]


def type_group(value):
    """Heuristic labels ONLY, not validated inpatient classification."""
    name = (value or "").strip().lower()
    if not name:
        return "missing"
    if name in {"ip", "imp"} or "inpatient" in name:
        return "inpatient_label_candidate"
    if "emergency" in name or name in {"ed", "er"}:
        return "emergency_label_candidate"
    if "observation" in name:
        return "observation_label_candidate"
    if "outpatient" in name or "ambulatory" in name:
        return "outpatient_label_candidate"
    return "unclassified"


def code_system_group(raw):
    val = (raw or "").strip().upper()
    if val in {"CPT", "HCPCS", "SNOMED", "ICD-10-PCS", "ICD-9-CM"}:
        return val
    return "other_or_missing"


def find_members(archive):
    found = {}
    for item in archive.infolist():
        if item.is_dir():
            continue
        base = item.filename.replace("\\", "/").split("/")[-1].lower()
        if base in TABLES:
            if base in found:
                raise ValueError("Duplicate required table basename: " + base)
            found[base] = item.filename
    if set(found) != set(TABLES):
        raise ValueError("Missing required clinical table(s): " + ", ".join(sorted(set(TABLES) - set(found))))
    return found


def preflight_match(archive, paths, prior):
    if prior.get("stage") != "STEP36_RESEARCH_METADATA_PREFLIGHT":
        raise ValueError("Step36 report does not have the expected stage")
    if prior.get("schema_supports_attempted_encounter_linkage") is not True:
        raise ValueError("Step36 did not establish structural readiness")
    for name in TABLES:
        record = prior.get("files", {}).get(name, {})
        if not record.get("present") or record.get("missing_expected_fields"):
            raise ValueError("Step36 reported a missing field/table: " + name)
        if record.get("uncompressed_bytes") != archive.getinfo(paths[name]).file_size:
            raise ValueError("Step36 ZIP signature mismatch: " + name)


def sample(archive, member, table, maximum):
    """Only consume the first maximum data rows; keep in-memory identifiers."""
    rows = []
    with archive.open(member) as raw:
        with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = set(reader.fieldnames or ())
            if missing := FIELDS[table] - headers:
                raise ValueError("Missing required headers for " + table + ": " + ",".join(sorted(missing)))
            for row in itertools.islice(reader, maximum):
                rows.append(row)
    return rows


def summarize(rows, table):
    missing_encounter = 0
    missing_patient = 0
    years = Counter()
    date_shapes = Counter()
    ambiguous_date_count = 0
    specifics = Counter()
    encounter_patient = {}
    conflicting_encounter_patient = 0
    duplicate_encounter_rows = 0
    nonblank_pairs = []
    missing_source_id = 0
    conflicting_encounter_source = 0
    encounter_source = {}
    for row in rows:
        encounter_id = (row.get("encounter_id") or "").strip()
        patient_id = (row.get("patient_id") or "").strip()
        if not encounter_id:
            missing_encounter += 1
        if not patient_id:
            missing_patient += 1
        source_id = (row.get("source_id") or "").strip()
        if "source_id" in row and not source_id:
            missing_source_id += 1
        if encounter_id and patient_id:
            nonblank_pairs.append((encounter_id, patient_id))
        year_col = "start_date" if table == "encounter.csv" else "date"
        shape, year_bucket, ambiguous_date = date_profile(row.get(year_col))
        years[year_bucket] += 1
        date_shapes[shape] += 1
        ambiguous_date_count += int(ambiguous_date)
        if table == "encounter.csv":
            specifics[type_group(row.get("type"))] += 1
            if encounter_id:
                if encounter_id in encounter_patient:
                    duplicate_encounter_rows += 1
                    if patient_id != encounter_patient[encounter_id]:
                        conflicting_encounter_patient += 1
                else:
                    encounter_patient[encounter_id] = patient_id
                if encounter_id in encounter_source and source_id != encounter_source[encounter_id]:
                    conflicting_encounter_source += 1
                encounter_source.setdefault(encounter_id, source_id)
        elif table == "diagnosis.csv":
            if (row.get("code_system") or "").strip().upper() == "ICD-10-CM" and re.match(
                r"^I63(?:\.|$)", (row.get("code") or "").strip().upper()
            ):
                specifics["icd10cm_I63"] += 1
            if (row.get("principal_diagnosis_indicator") or "").strip().upper() == "P":
                specifics["literal_P_principal_indicator"] += 1
        else:
            group = code_system_group(row.get("code_system"))
            specifics[group] += 1
            if group == "CPT" and (row.get("code") or "").strip() in CPT14:
                specifics["CPT_14_catalog_code"] += 1
    return {
        "rows_examined": len(rows),
        "max_rows_exhausted_or_table_finished": None,  # set by caller
        "missing_encounter_id_n": private_count(missing_encounter),
        "missing_patient_id_n": private_count(missing_patient),
        "missing_source_id_n": private_count(missing_source_id) if rows and "source_id" in rows[0] else None,
        "nonblank_encounter_patient_pairs_n": private_count(len(nonblank_pairs)),
        "sample_distinct_nonblank_encounter_ids_n": private_count(
            len({pair[0] for pair in nonblank_pairs})
        ),
        "coarse_date_bucket_counts": {k: private_count(v) for k, v in sorted(years.items())},
        "date_shape_category_counts": {
            k: private_count(v) for k, v in sorted(date_shapes.items())
        },
        "year_last_month_day_ambiguous_n": private_count(ambiguous_date_count),
        "restricted_characteristic_counts": {
            k: private_count(v) for k, v in sorted(specifics.items())
        },
        "sample_duplicate_encounter_id_rows_n": (
            private_count(duplicate_encounter_rows) if table == "encounter.csv" else None
        ),
        "sample_encounter_id_conflicting_patient_n": (
            private_count(conflicting_encounter_patient) if table == "encounter.csv" else None
        ),
        "sample_encounter_id_conflicting_source_n": (
            private_count(conflicting_encounter_source) if table == "encounter.csv" and rows and "source_id" in rows[0] else None
        ),
    }


def sample_overlap(events, parent):
    with_id = 0
    in_parent = 0
    same_patient = 0
    differing_patient = 0
    agreeing_source = 0
    differing_source = 0
    for row in events:
        encounter_id = (row.get("encounter_id") or "").strip()
        if not encounter_id:
            continue
        with_id += 1
        if encounter_id in parent:
            in_parent += 1
            parent_patient, parent_source = parent[encounter_id]
            if parent_patient and (row.get("patient_id") or "").strip() == parent_patient:
                same_patient += 1
            else:
                differing_patient += 1
            event_source = (row.get("source_id") or "").strip()
            if parent_source and event_source:
                if event_source == parent_source:
                    agreeing_source += 1
                else:
                    differing_source += 1
    return {
        "sample_event_rows_with_encounter_id_n": private_count(with_id),
        "encounter_id_seen_in_encounter_prefix_n": private_count(in_parent),
        "matching_patient_id_when_observed_n": private_count(same_patient),
        "missing_or_different_patient_id_when_observed_n": private_count(differing_patient),
        "agreeing_nonblank_source_id_when_observed_n": private_count(agreeing_source),
        "differing_nonblank_source_id_when_observed_n": private_count(differing_source),
        "interpretation": "Prefix-to-prefix overlap only; absence of matches does not indicate failed source-wide linkage.",
    }


def output_dir_guard(directory):
    allowed = PHASE1.resolve()
    if allowed != ROOT.resolve() / "results" / "phase1":
        raise ValueError("results/phase1 must not be a symlink outside the cloned repository")
    resolved = directory.expanduser().resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("Output directory must be within the cloned repository results/phase1/")
    return resolved


def atomic_private_json(output, payload):
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix=".step37_", dir=str(output.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, output)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_private_zip(output, json_path):
    fd, tmp = tempfile.mkstemp(prefix=".step37zip_", dir=str(output.parent))
    try:
        with os.fdopen(fd, "wb") as dest:
            with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.write(json_path, arcname=REPORT_NAME)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, output)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def run(archive_path, preflight_path, output_directory, max_rows):
    if not 1 <= max_rows <= 200000:
        raise ValueError("--max-rows-per-table must be 1..200000")
    out = output_dir_guard(output_directory)
    result_path, bundle_path = out / REPORT_NAME, out / ZIP_NAME
    source_resolved = archive_path.expanduser().resolve()
    for target in (result_path, bundle_path):
        if target.resolve() == source_resolved:
            raise ValueError("Source ZIP cannot be an output path")
    preflight_blob = preflight_path.read_bytes()
    prior = json.loads(preflight_blob)
    with zipfile.ZipFile(archive_path) as archive:
        members = find_members(archive)
        preflight_match(archive, members, prior)
        sampled = {
            table: sample(archive, members[table], table, max_rows)
            for table in TABLES
        }
    parent = {}
    for row in sampled["encounter.csv"]:
        key = (row.get("encounter_id") or "").strip()
        if key and key not in parent:
            parent[key] = (
                (row.get("patient_id") or "").strip(),
                (row.get("source_id") or "").strip(),
            )
    summaries = {k: summarize(v, k) for k, v in sampled.items()}
    for table in TABLES:
        summaries[table]["max_rows_exhausted_or_table_finished"] = (
            len(sampled[table]) == max_rows
        )
    report = {
        "stage": "STEP37_RESEARCH_ENCOUNTER_BOUNDED_PILOT",
        "input_step36_sha256": hashlib.sha256(preflight_blob).hexdigest(),
        "max_rows_per_clinical_table": max_rows,
        "sampling_method": "first_n_rows_per_table_NOT_RANDOM",
        "exhaustive_clinical_scan": False,
        "patient_level_rows_or_identifiers_exported": False,
        "source_tables": summaries,
        "sample_overlap": {
            name: sample_overlap(sampled[name], parent)
            for name in ("diagnosis.csv", "procedure.csv")
        },
        "encounter_linkage_validated_for_study_population": False,
        "inpatient_encounter_types_clinically_validated": False,
        "imaging_capture_validated": False,
        "ready_for_clinical_disparities_models": False,
        "interpretation_limits": [
            "Each sample is an independent, possibly sorted file prefix; sampling is not random.",
            "Prefix encounter joins are diagnostic only; missing overlap is not evidence of bad real-world keys.",
            "Encounter type labels are lexical candidates, NOT proof of inpatient admission.",
            "Year-last slash dates can have ambiguous month/day order even when their calendar year is valid.",
            "Unrecognized date shapes must be investigated locally before day-level episode matching.",
            "Patient/encounter/source identifiers may have cross-site scope; review source_id agreement when available.",
            "I63 and imaging-CPT signals in sampled rows are not patient rates or codebook validation.",
            "All numbers require data-use/disclosure review; do not commit generated outputs.",
        ],
    }
    atomic_private_json(result_path, report)
    atomic_private_zip(bundle_path, result_path)
    print("Step37 bounded pilot completed (no full clinical scan).")
    print("Sample rows per table:", {k: len(v) for k, v in sampled.items()})
    print("Aggregate JSON:", result_path)
    print("Review ZIP:", bundle_path)
    print("Encounter/clinical inference remains UNVERIFIED.")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True, help="Existing Research Network source ZIP")
    p.add_argument("--step36-json", type=Path, default=STEP36)
    p.add_argument("--output-dir", type=Path, default=PHASE1)
    p.add_argument("--max-rows-per-table", type=int, default=50000)
    args = p.parse_args()
    run(args.zip, args.step36_json, args.output_dir, args.max_rows_per_table)


if __name__ == "__main__":
    main()
