#!/usr/bin/env python3
"""Step60: privately review the existing three Step59 aggregate reports.

NO source ZIP, clinical rows, patient identifiers, or full-table scans.
Reads only existing ignored private JSON reports. Does not authorize an
analysis, infer HCO coverage or completed imaging, or select a study end year.
The generated report is private, not approved for upload or publication.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "results" / "phase1" / "full_reconstruction_private" / "source_wide_qa"
OUTPUT = PRIVATE / "step60_local_aggregate_review_LOCAL_ONLY.json"
ACK = "I_CONFIRM_LOCAL_PRIVATE_AGGREGATE_REVIEW"
STAGES = ("encounter", "diagnosis", "procedure")
STAGE_MARKER = "STEP59_FULL_SOURCE_AGGREGATE_QA_LOCAL_ONLY"
YEARS_SPECIAL = frozenset(("BEFORE_2016", "AFTER_CURRENT_YEAR", "MISSING", "INVALID"))
GROUP_CATEGORIES = {
    "encounter": ("encounter_type_by_year_bucket_NOT_INPATIENT_ADMISSIONS",
                  frozenset(("IMP", "EMER", "OTHER_OR_EMPTY"))),
    "diagnosis": ("code_system_by_year_bucket_NOT_PERFORMED_PROCEDURES",
                  frozenset(("CPT", "SNOMED", "HCPCS", "ICD-10-PCS", "ICD-9-CM",
                             "ICD-10-CM", "OTHER_OR_EMPTY"))),
    "procedure": ("code_system_by_year_bucket_NOT_PERFORMED_PROCEDURES",
                  frozenset(("CPT", "SNOMED", "HCPCS", "ICD-10-PCS", "ICD-9-CM",
                             "ICD-10-CM", "OTHER_OR_EMPTY"))),
}
IMAGING_GROUPS = frozenset(("CPT14_CORE_CODE_ROWS",
                            "CTA_HEAD_NECK_70471_CANDIDATE",
                            "CT_PERFUSION_SEPARATE"))


def _count(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Invalid nonnegative aggregate counter")
    return value


def _year(value, current_year):
    if value in YEARS_SPECIAL:
        return value
    if not isinstance(value, str) or not (len(value) == 4 and value.isdigit()):
        raise ValueError("Unknown calendar year bucket")
    year = int(value)
    if not 2016 <= year <= current_year:
        raise ValueError("Calendar year bucket outside guarded 2016+ period")
    return value


def _year_map(obj, current_year):
    if not isinstance(obj, dict):
        raise ValueError("Invalid year aggregate mapping")
    return {_year(k, current_year): _count(v) for k, v in obj.items()}


def _two_key_map(obj, allowed, current_year):
    if not isinstance(obj, dict):
        raise ValueError("Invalid category aggregate mapping")
    result = {}
    for key, value in obj.items():
        if not isinstance(key, str) or key.count("|") != 1:
            raise ValueError("Malformed year/category aggregate bucket")
        year, category = key.split("|")
        year = _year(year, current_year)
        if category not in allowed:
            raise ValueError("Unexpected category in aggregate report")
        result[(year, category)] = _count(value)
    return result


def validate_report(report, stage, current_year=None, datefix_v2=False):
    """Validate internal consistency of an already-completed Step59 report."""
    if current_year is None:
        current_year = date.today().year
    if not isinstance(report, dict) or report.get("stage") != STAGE_MARKER:
        raise ValueError("Report is not a Step59 aggregate QA artifact")
    if report.get("table") != stage + ".csv":
        raise ValueError("Step59 report table does not match required stage")
    expected_parser = "YYYYMMDD_OR_ISO8601_VALIDATED_V2" if datefix_v2 else None
    if report.get("date_parser_version") != expected_parser:
        raise ValueError("Step59 date-parser version mismatch; mixing legacy and v2 reports prohibited")
    if (report.get("source_clinical_table_scanned_completely") is not True
            or report.get("full_cohort_reconstruction_performed") is not False
            or report.get("sharing_requires_disclosure_review") is not True):
        raise ValueError("Step59 completion/disclosure guard failed")
    for flag in ("HCO_linkage_verified", "imaging_completion_verified",
                 "final_study_end_year_approved"):
        if report.get(flag) is not False:
            raise ValueError("Step59 clinical/coverage verification flag unexpected")
    obj = report.get("result")
    if not isinstance(obj, dict) or obj.get("patient_identifiers_emitted") is not False or obj.get("encounter_identifiers_emitted") is not False:
        raise ValueError("Step59 report is missing privacy safeguards")
    total = _count(obj.get("rows_scanned"))
    by_year = _year_map(obj.get("rows_by_year_bucket_NOT_COVERAGE_VERIFIED"), current_year)
    if sum(by_year.values()) != total:
        raise ValueError("Step59 row totals do not reconcile")
    missing = obj.get("missing_required_values")
    if not isinstance(missing, dict):
        raise ValueError("Missing field-count mapping absent")
    allowed_missing = {
        "encounter": frozenset(("patient_id", "encounter_id", "type", "start_date", "end_date")),
        "diagnosis": frozenset(("patient_id", "encounter_id", "date", "code_system", "code", "principal_diagnosis_indicator")),
        "procedure": frozenset(("patient_id", "encounter_id", "date", "code_system", "code")),
    }[stage]
    if set(missing) - allowed_missing:
        raise ValueError("Unexpected missingness field")
    for field, count in missing.items():
        if _count(count) > total:
            raise ValueError("Missing field count exceeds source rows")
    group_key, groups_allowed = GROUP_CATEGORIES[stage]
    grouped = _two_key_map(obj.get(group_key), groups_allowed, current_year)
    recon = Counter()
    for (year, _), count in grouped.items():
        recon[year] += count
    if dict(recon) != {k: v for k, v in by_year.items() if v != 0}:
        raise ValueError("Stage-by-year subgroup counts do not reconcile")
    if stage == "diagnosis":
        principal = _two_key_map(obj.get("principal_indicator_by_year_bucket_NOT_VALIDATED"),
                                 frozenset(("P", "OTHER_OR_EMPTY")), current_year)
        principal_recon = Counter()
        for (year, _), count in principal.items():
            principal_recon[year] += count
        if dict(principal_recon) != {k: v for k, v in by_year.items() if v != 0}:
            raise ValueError("Principal-flag counts do not reconcile")
    else:
        principal = {}
    if stage == "procedure":
        imaging = _two_key_map(obj.get("imaging_code_rows_by_year_NOT_SCANS_OR_PATIENTS"),
                               IMAGING_GROUPS, current_year)
        cpt_per_year = {year: value for (year, system), value in grouped.items()
                        if system == "CPT"}
        imaging_recon = Counter()
        for (year, _), count in imaging.items():
            imaging_recon[year] += count
        for year, count in imaging_recon.items():
            if count > cpt_per_year.get(year, 0):
                raise ValueError("Imaging CPT-code counts exceed CPT procedure rows")
    else:
        imaging = {}
    return {
        "rows": total,
        "year_counts": by_year,
        "group_counts": grouped,
        "principal_counts": principal,
        "imaging_counts": imaging,
        "missing_field_counts": missing,
    }


def build_review(reports, current_year=None, datefix_v2=False):
    """Private review only, no automated year approval or phenotype execution."""
    if current_year is None:
        current_year = date.today().year
    if not isinstance(reports, dict) or set(reports) != set(STAGES):
        raise ValueError("Exactly three completed Step59 reports are required")
    checked = {stage: validate_report(reports[stage], stage, current_year,
                                      datefix_v2=datefix_v2)
               for stage in STAGES}
    if datefix_v2 and any(not any(k not in YEARS_SPECIAL and v > 0
                                   for k, v in checked[stage]["year_counts"].items())
                          for stage in STAGES):
        raise ValueError("Corrected dates still unparseable in one or more source tables")
    years = sorted({year for data in checked.values() for year in data["year_counts"]
                    if year not in YEARS_SPECIAL}, key=int)
    by_year = {}
    for year in years:
        by_year[year] = {}
        for stage, data in checked.items():
            n = data["year_counts"].get(year, 0)
            row = {"source_rows": n,
                   "within_table_percentage": None if not data["rows"]
                      else round(100 * n / data["rows"], 4)}
            for (bucket, category), value in data["group_counts"].items():
                if bucket == year:
                    row[category] = value
            if stage == "procedure":
                row["CPT14_CODE_ROWS_NOT_EXAMS"] = data["imaging_counts"].get(
                    (year, "CPT14_CORE_CODE_ROWS"), 0)
                row["COMBINED_CTA_70471_CANDIDATE_ROWS"] = data["imaging_counts"].get(
                    (year, "CTA_HEAD_NECK_70471_CANDIDATE"), 0)
                row["CT_PERFUSION_SEPARATE_ROWS"] = data["imaging_counts"].get(
                    (year, "CT_PERFUSION_SEPARATE"), 0)
            by_year[year][stage] = row
    special = {
        stage: {name: info["year_counts"].get(name, 0)
                for name in sorted(YEARS_SPECIAL)}
        for stage, info in checked.items()
    }
    procedure = checked["procedure"]
    cpt = sum(v for (year, system), v in procedure["group_counts"].items()
              if system == "CPT")
    other_system = sum(v for (year, system), v in procedure["group_counts"].items()
                       if system != "CPT")
    core = sum(v for (year, category), v in procedure["imaging_counts"].items()
               if category == "CPT14_CORE_CODE_ROWS")
    flags = {
        "missing_or_invalid_dates_in_any_table":
            any(info["year_counts"].get("MISSING", 0) or
                info["year_counts"].get("INVALID", 0) for info in checked.values()),
        "procedure_rows_non_CPT_present": other_system > 0,
        "CPT14_rows_absent_in_procedure_records": core == 0,
        "2026_or_later_CPT70471_review_needed":
            any(category == "CTA_HEAD_NECK_70471_CANDIDATE" and count > 0
                for (year, category), count in procedure["imaging_counts"].items()),
        "cross_table_calendar_year_presence_differs":
            any(any(data["year_counts"].get(year, 0) == 0 for data in checked.values())
                for year in years),
        "site_HCO_participation_unknown": True,
        "procedure_performed_vs_ordered_unknown": True,
        "ICD10_stroke_phenotype_not_validated": True,
        "year_completeness_not_validated": True,
    }
    return {
        "stage": "STEP60_LOCAL_PRIVATE_STEP59_REVIEW",
        "date_parser_version": ("YYYYMMDD_OR_ISO8601_VALIDATED_V2"
                                if datefix_v2 else None),
        "source": "THREE_EXISTING_STEP59_PRIVATE_REPORTS_ONLY",
        "all_three_step59_artifacts_validated": True,
        "no_source_clinical_rows_read": True,
        "no_patient_or_encounter_identifiers_returned": True,
        "sharing_requires_disclosure_review": True,
        "final_study_end_year": None,
        "calendar_years_present_NOT_APPROVED": years,
        "private_table_row_counts_NOT_PATIENTS": {
            stage: checked[stage]["rows"] for stage in STAGES},
        "private_year_by_table_NOT_SITE_ADJUSTED": by_year,
        "private_special_date_buckets": special,
        "private_missing_field_counts": {
            stage: checked[stage]["missing_field_counts"] for stage in STAGES},
        "private_procedure_CPT_rows_NOT_IMAGING_RATE": cpt,
        "private_procedure_non_CPT_rows_NOT_IMAGING_RATE": other_system,
        "automated_review_flags_NOT_CLINICAL_SIGNOFF": flags,
        "review_required": [
            "Review year-by-year trends and partial-year dates using source coverage metadata",
            "Verify HCO participation; Step59 lacks HCO-specific counts",
            "Verify procedure coding-system and completed-vs-ordered semantics",
            "Determine whether CPT14 misses non-CPT brain/vascular imaging",
            "Verify stroke diagnosis principal indicator and cohort definitions",
            "Retain Step45 hard-block; design approved phenotype extractor separately",
        ],
    }


def read_reports(private_dir=PRIVATE, datefix_v2=False):
    """Read only exact local private Stage59 filenames; no source ZIP access."""
    directory = Path(private_dir)
    docs = {}
    for stage in STAGES:
        suffix = "_DATEFIX_V2_LOCAL_ONLY.json" if datefix_v2 else "_LOCAL_ONLY.json"
        file = directory / ("step59_" + stage + suffix)
        if file.is_symlink() or not file.is_file():
            raise ValueError("Required private Step59 report missing or unsafe")
        if file.stat().st_size > 2_000_000:
            raise ValueError("Step59 private report unexpectedly large")
        with file.open("r", encoding="utf-8") as handle:
            docs[stage] = json.load(handle)
    return docs


def write_review(review, output=OUTPUT, private_dir=PRIVATE):
    folder = Path(private_dir).resolve()
    location = Path(output).resolve()
    if location.parent != folder or Path(output).is_symlink():
        raise ValueError("Review must remain in designated local private QA folder")
    if not folder.is_dir() or folder.stat().st_mode & 0o077:
        raise PermissionError("Local private QA directory is absent or not mode 0700")
    if location.exists():
        raise FileExistsError("Private Step60 review exists; no overwrite")
    fd, temp_path = tempfile.mkstemp(prefix=".step60_", dir=str(folder))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(review, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.link(temp_path, location)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    return location


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acknowledge", required=True,
                        help="Confirm private local review permitted under existing study protocol")
    parser.add_argument("--datefix-v2", action="store_true",
                        help="Reconcile corrected v2 date outputs, never legacy reports")
    options = parser.parse_args(argv)
    if options.acknowledge != ACK:
        parser.error("Explicit local privacy acknowledgment is required")
    output = (PRIVATE / "step60_local_aggregate_review_DATEFIX_V2_LOCAL_ONLY.json"
              if options.datefix_v2 else OUTPUT)
    if output.exists():
        parser.error("Step60 private review already exists; refusing overwrite")
    review = build_review(read_reports(datefix_v2=options.datefix_v2),
                          datefix_v2=options.datefix_v2)
    saved = write_review(review, output=output)
    print("Step60 private review completed; 3 prior Step59 aggregate reports reconciled.")
    print("Private result:", saved)
    print("Do not upload, paste or publish this private report.")
    print("Study end year remains UNKNOWN; no cohort extraction performed.")


if __name__ == "__main__":
    main()
