#!/usr/bin/env python3
"""Conservative coarse disclosure CANDIDATE from existing local Step60 JSON.

No TriNetX ZIP, patient-level records or Step59 source scans are read.
No output is approved for external sharing by this code. A human must check
research agreement, cell suppression and cumulative disclosure risk.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "results" / "phase1" / "full_reconstruction_private" / "source_wide_qa"
SOURCE = PRIVATE / "step60_local_aggregate_review_LOCAL_ONLY.json"
OUTPUT = PRIVATE / "step61_disclosure_candidate_LOCAL_ONLY.json"
ACK = "I_CONFIRM_PRIVATE_DISCLOSURE_CANDIDATE_ONLY"
MIN_DENOMINATOR = 1000
MIN_CONTRAST_CELL = 50
STAGES = ("encounter", "diagnosis", "procedure")
SYSTEMS = ("CPT", "SNOMED", "HCPCS", "ICD-10-PCS", "ICD-9-CM", "ICD-10-CM", "OTHER_OR_EMPTY")


def _count(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Step60 invalid nonnegative aggregate counter")
    return value


def _validate(report, current_year):
    """Fail closed if aggregate report layout/provenance is unexpected."""
    if (not isinstance(report, dict)
            or report.get("stage") != "STEP60_LOCAL_PRIVATE_STEP59_REVIEW"
            or report.get("source") != "THREE_EXISTING_STEP59_PRIVATE_REPORTS_ONLY"
            or report.get("all_three_step59_artifacts_validated") is not True
            or report.get("no_source_clinical_rows_read") is not True
            or report.get("no_patient_or_encounter_identifiers_returned") is not True
            or report.get("sharing_requires_disclosure_review") is not True
            or report.get("final_study_end_year") is not None):
        raise ValueError("Step60 provenance or disclosure flags invalid")
    totals = report.get("private_table_row_counts_NOT_PATIENTS")
    years = report.get("private_year_by_table_NOT_SITE_ADJUSTED")
    if not isinstance(totals, dict) or set(totals) != set(STAGES):
        raise ValueError("Step60 table totals invalid")
    for table in STAGES:
        _count(totals[table])
    if not isinstance(years, dict) or len(years) > current_year - 2015:
        raise ValueError("Unexpected year-bucket mapping")
    validated = {}
    cumulative = {table: 0 for table in STAGES}
    for year, value in years.items():
        if (not isinstance(year, str) or len(year) != 4 or not year.isascii()
                or not year.isdigit() or not 2016 <= int(year) <= current_year):
            raise ValueError("Unrecognized year bucket")
        if not isinstance(value, dict) or set(value) != set(STAGES):
            raise ValueError("Step60 year missing core table")
        validated[year] = {}
        for table in STAGES:
            info = value[table]
            if not isinstance(info, dict):
                raise ValueError("Invalid per-year aggregate")
            n = _count(info.get("source_rows"))
            cumulative[table] += n
            validated[year][table] = {"source_rows": n}
            if table == "procedure":
                seen = 0
                for system in SYSTEMS:
                    amount = _count(info.get(system, 0))
                    validated[year][table][system] = amount
                    seen += amount
                if seen != n:
                    raise ValueError("Yearly procedure code-system totals do not reconcile")
                for signal in ("CPT14_CODE_ROWS_NOT_EXAMS", "COMBINED_CTA_70471_CANDIDATE_ROWS", "CT_PERFUSION_SEPARATE_ROWS"):
                    validated[year][table][signal] = _count(info.get(signal, 0))
                if sum(validated[year][table][signal] for signal in
                       ("CPT14_CODE_ROWS_NOT_EXAMS", "COMBINED_CTA_70471_CANDIDATE_ROWS", "CT_PERFUSION_SEPARATE_ROWS")) > validated[year][table]["CPT"]:
                    raise ValueError("CPT imaging groups exceed source CPT rows")
    if any(cumulative[table] > totals[table] for table in STAGES):
        raise ValueError("Year totals exceed source rows")
    return validated


def _trend(current, previous):
    if current * 2 < previous:
        return "down_more_than_50pct"
    if current * 5 < previous * 4:
        return "down_20_to_50pct"
    if current * 4 > previous * 6:
        return "up_more_than_50pct"
    if current * 4 > previous * 5:
        return "up_25_to_50pct"
    return "roughly_similar"


def _mix(cpt, other):
    """Only release a broad class when both binary complement cells are large."""
    total = cpt + other
    if total < MIN_DENOMINATOR or min(cpt, other) < MIN_CONTRAST_CELL:
        return "withheld"
    # Coarse 1/3, 2/3 categories; no percentages, no counts.
    if cpt * 3 < total:
        return "mostly_non_CPT"
    if cpt * 3 > total * 2:
        return "mostly_CPT"
    return "mixed_CPT_and_non_CPT"


def _cpt14_presence(core, cpt):
    if cpt < MIN_DENOMINATOR or core < MIN_CONTRAST_CELL or cpt - core < MIN_CONTRAST_CELL:
        return "withheld_not_evidence_of_absence"
    return "recorded_core_CPT_codes_present_in_large_aggregate_NOT_scans"


def summarize(report, current_year=None):
    if current_year is None:
        current_year = date.today().year
    rows = _validate(report, current_year)
    by_year = []
    prior_year = None
    prior_rows = None
    for year in sorted(rows):
        item = rows[year]
        # Suppress the WHOLE year if any source table has a small annual denominator.
        if any(item[stage]["source_rows"] < MIN_DENOMINATOR for stage in STAGES):
            prior_year, prior_rows = None, None
            continue
        entry = {
            "calendar_year_observed_NOT_completeness_approved": year,
            "current_calendar_year_can_be_partial": int(year) == current_year,
            "year_to_previous_adjacent_released_year_row_volume_pattern": "not_available",
            "procedure_CPT_vs_other_systems": "withheld",
            "core_CPT14_qualitative_signal": "withheld_not_evidence_of_absence",
        }
        if prior_year is not None and int(year) == int(prior_year) + 1:
            entry["year_to_previous_adjacent_released_year_row_volume_pattern"] = {
                stage: _trend(item[stage]["source_rows"], prior_rows[stage]["source_rows"])
                for stage in STAGES
            }
        p = item["procedure"]
        cpt = p["CPT"]
        other = p["source_rows"] - cpt
        entry["procedure_CPT_vs_other_systems"] = _mix(cpt, other)
        entry["core_CPT14_qualitative_signal"] = _cpt14_presence(p["CPT14_CODE_ROWS_NOT_EXAMS"], cpt)
        by_year.append(entry)
        prior_year, prior_rows = year, item
    return {
        "artifact": "STEP61_COARSE_DISCLOSURE_CANDIDATE",
        "disclosure_status": "NOT_APPROVED_BY_SCRIPT_USER_MUST_REVIEW",
        "source": "LOCAL_STEP60_AGGREGATES_ONLY_NO_SOURCE_ZIP",
        "years_below_aggregate_reporting_threshold": "omitted_without_count_or_identity",
        "minimum_annual_rows_per_each_of_three_tables": MIN_DENOMINATOR,
        "minimum_contrast_cell_for_qualitative_binary_indicators": MIN_CONTRAST_CELL,
        "clinical_record_or_patient_counts_included": False,
        "exact_source_row_counts_included": False,
        "exact_rates_or_percentages_included": False,
        "hospital_or_organization_identifiers_included": False,
        "study_end_year_selected": False,
        "data_completeness_validated": False,
        "imaging_completion_validated": False,
        "recorded_CPT_code_is_not_proof_of_completed_scan": True,
        "provisional_coarse_year_summary": by_year,
        "scientific_questions_for_reviewer": [
            "Are calendar-year row volumes unusually changing across tables? These are not patient denominators.",
            "Is there mixed CPT and non-CPT procedure coding requiring modality mapping and capture checks?",
            "Could the current calendar year be partial, and is HCO participation stable? Not determined here.",
            "What do procedure event records and principal-diagnosis flags actually mean in this source?",
        ],
        "human_disclosure_review_required_before_external_upload": True,
        "note": "Coarse trends may still disclose institution-restricted research metadata. Never treat this as automatic clearance.",
    }


def read_private(path=SOURCE):
    file = Path(path)
    if file.is_symlink() or not file.is_file() or file.stat().st_size > 2_000_000:
        raise ValueError("Expected safe local Step60 report unavailable")
    with file.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_private(report, output=OUTPUT, folder=PRIVATE):
    root = Path(folder).resolve()
    path = Path(output)
    if path.is_symlink() or path.resolve().parent != root:
        raise ValueError("Step61 output must be inside dedicated private QA folder")
    if not root.is_dir() or root.stat().st_mode & 0o077:
        raise PermissionError("Private report folder missing or permissions not 0700")
    if path.exists():
        raise FileExistsError("Disclosure candidate already exists; no overwrite")
    fd, temp = tempfile.mkstemp(prefix=".step61_", dir=str(root))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.link(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acknowledge", required=True)
    args = parser.parse_args(argv)
    if args.acknowledge != ACK:
        parser.error("Explicit private-candidate review acknowledgement required")
    if OUTPUT.exists():
        parser.error("Private disclosure candidate already exists; refusing overwrite")
    report = summarize(read_private())
    target = write_private(report)
    print("Step61 coarse disclosure candidate prepared locally.")
    print("Private candidate:", target)
    print("No source clinical tables were accessed. Do not upload without disclosure approval.")


if __name__ == "__main__":
    main()
