"""Synthetic-only Step60 reconciliation: no clinical data, source archive, or PHI."""
import copy
import json
import stat

import pytest

from scripts import step60_local_aggregate_review as s


def fixture_report(table, counts, category_key, grouped, *, principal=None, imaging=None, missing=None):
    r = {
        "stage": "STEP59_FULL_SOURCE_AGGREGATE_QA_LOCAL_ONLY",
        "table": table + ".csv",
        "source_clinical_table_scanned_completely": True,
        "full_cohort_reconstruction_performed": False,
        "HCO_linkage_verified": False,
        "imaging_completion_verified": False,
        "final_study_end_year_approved": False,
        "sharing_requires_disclosure_review": True,
        "result": {
            "rows_scanned": sum(counts.values()),
            "rows_by_year_bucket_NOT_COVERAGE_VERIFIED": counts,
            "missing_required_values": missing or {},
            "code_system_by_year_bucket_NOT_PERFORMED_PROCEDURES": {},
            "encounter_type_by_year_bucket_NOT_INPATIENT_ADMISSIONS": {},
            "principal_indicator_by_year_bucket_NOT_VALIDATED": {},
            "imaging_code_rows_by_year_NOT_SCANS_OR_PATIENTS": {},
            "patient_identifiers_emitted": False,
            "encounter_identifiers_emitted": False,
        },
    }
    r["result"][category_key] = grouped
    if principal is not None:
        r["result"]["principal_indicator_by_year_bucket_NOT_VALIDATED"] = principal
    if imaging is not None:
        r["result"]["imaging_code_rows_by_year_NOT_SCANS_OR_PATIENTS"] = imaging
    return r


@pytest.fixture
def three():
    encounter = fixture_report(
        "encounter", {"2016": 3, "2017": 1, "INVALID": 1},
        "encounter_type_by_year_bucket_NOT_INPATIENT_ADMISSIONS",
        {"2016|IMP": 2, "2016|EMER": 1, "2017|IMP": 1,
         "INVALID|OTHER_OR_EMPTY": 1},
        missing={"end_date": 1},
    )
    diagnosis = fixture_report(
        "diagnosis", {"2016": 2, "2017": 1, "MISSING": 1},
        "code_system_by_year_bucket_NOT_PERFORMED_PROCEDURES",
        {"2016|ICD-10-CM": 2, "2017|ICD-10-CM": 1,
         "MISSING|ICD-10-CM": 1},
        principal={"2016|P": 1, "2016|OTHER_OR_EMPTY": 1,
                   "2017|P": 1, "MISSING|OTHER_OR_EMPTY": 1},
        missing={"date": 1},
    )
    procedure = fixture_report(
        "procedure", {"2016": 4, "2017": 2, "2026": 1},
        "code_system_by_year_bucket_NOT_PERFORMED_PROCEDURES",
        {"2016|CPT": 2, "2016|SNOMED": 2,
         "2017|CPT": 1, "2017|OTHER_OR_EMPTY": 1, "2026|CPT": 1},
        imaging={"2016|CPT14_CORE_CODE_ROWS": 1,
                 "2017|CPT14_CORE_CODE_ROWS": 1,
                 "2026|CTA_HEAD_NECK_70471_CANDIDATE": 1},
    )
    return {"encounter": encounter, "diagnosis": diagnosis, "procedure": procedure}


def test_reconcile_three_reports_and_always_defer_year_signoff(three):
    result = s.build_review(three, current_year=2026)
    assert result["all_three_step59_artifacts_validated"] is True
    assert result["no_source_clinical_rows_read"] is True
    assert result["final_study_end_year"] is None
    assert result["calendar_years_present_NOT_APPROVED"] == ["2016", "2017", "2026"]
    assert result["private_procedure_CPT_rows_NOT_IMAGING_RATE"] == 4
    assert result["private_procedure_non_CPT_rows_NOT_IMAGING_RATE"] == 3
    assert result["private_year_by_table_NOT_SITE_ADJUSTED"]["2016"]["procedure"]["CPT14_CODE_ROWS_NOT_EXAMS"] == 1
    assert result["private_year_by_table_NOT_SITE_ADJUSTED"]["2026"]["procedure"]["COMBINED_CTA_70471_CANDIDATE_ROWS"] == 1
    flags = result["automated_review_flags_NOT_CLINICAL_SIGNOFF"]
    assert flags["missing_or_invalid_dates_in_any_table"]
    assert flags["procedure_rows_non_CPT_present"]
    assert flags["cross_table_calendar_year_presence_differs"]
    assert flags["2026_or_later_CPT70471_review_needed"]
    assert flags["site_HCO_participation_unknown"]


@pytest.mark.parametrize("deleted", s.STAGES)
def test_all_three_stages_are_required(three, deleted):
    three.pop(deleted)
    with pytest.raises(ValueError, match="Exactly three"):
        s.build_review(three, current_year=2026)


@pytest.mark.parametrize("stage", s.STAGES)
def test_partial_or_mislabelled_source_reports_rejected(three, stage):
    three[stage]["source_clinical_table_scanned_completely"] = False
    with pytest.raises(ValueError, match="completion/disclosure"):
        s.build_review(three, current_year=2026)


def test_report_cannot_be_shared_or_relabeled_as_approved(three):
    three["procedure"]["sharing_requires_disclosure_review"] = False
    with pytest.raises(ValueError, match="completion/disclosure"):
        s.build_review(three, current_year=2026)


def test_enforce_count_and_subcategory_reconciliation(three):
    three["diagnosis"]["result"]["rows_scanned"] += 1
    with pytest.raises(ValueError, match="row totals"):
        s.build_review(three, current_year=2026)


def test_enforce_subcategory_year_coverage(three):
    three["encounter"]["result"]["encounter_type_by_year_bucket_NOT_INPATIENT_ADMISSIONS"]["2016|IMP"] -= 1
    with pytest.raises(ValueError, match="subgroup counts"):
        s.build_review(three, current_year=2026)


def test_enforce_principal_indicator_partition(three):
    three["diagnosis"]["result"]["principal_indicator_by_year_bucket_NOT_VALIDATED"]["2016|P"] -= 1
    with pytest.raises(ValueError, match="Principal-flag"):
        s.build_review(three, current_year=2026)


def test_cpt14_cannot_exceed_all_cpt_procedure_rows(three):
    three["procedure"]["result"]["imaging_code_rows_by_year_NOT_SCANS_OR_PATIENTS"]["2016|CPT14_CORE_CODE_ROWS"] = 999
    with pytest.raises(ValueError, match="exceed CPT"):
        s.build_review(three, current_year=2026)


def test_malicious_category_and_count_rejected(three):
    r = copy.deepcopy(three)
    r["procedure"]["result"]["code_system_by_year_bucket_NOT_PERFORMED_PROCEDURES"]["2016|SYNTH_PATIENT_ROW"] = 0
    with pytest.raises(ValueError, match="Unexpected category"):
        s.build_review(r, current_year=2026)
    r = copy.deepcopy(three)
    r["procedure"]["result"]["code_system_by_year_bucket_NOT_PERFORMED_PROCEDURES"]["2016|CPT"] = True
    with pytest.raises(ValueError, match="nonnegative"):
        s.build_review(r, current_year=2026)


def test_private_file_io_and_no_overwrite(three, tmp_path):
    base = tmp_path / "private"
    base.mkdir(mode=0o700)
    for stage, report in three.items():
        target = base / ("step59_" + stage + "_LOCAL_ONLY.json")
        target.write_text(json.dumps(report), encoding="utf-8")
        target.chmod(0o600)
    result = s.build_review(s.read_reports(base), current_year=2026)
    out = base / "step60_local_aggregate_review_LOCAL_ONLY.json"
    s.write_review(result, output=out, private_dir=base)
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    assert json.loads(out.read_text())["final_study_end_year"] is None
    with pytest.raises(FileExistsError):
        s.write_review(result, output=out, private_dir=base)
    with pytest.raises(ValueError, match="designated"):
        s.write_review(result, output=tmp_path/"leak.json", private_dir=base)


def test_missing_or_unsafe_file_fails_without_scanning_source(three, tmp_path):
    with pytest.raises(ValueError, match="private Step59"):
        s.read_reports(tmp_path)
    other = tmp_path / "elsewhere.json"
    other.write_text("{}")
    (tmp_path / "step59_encounter_LOCAL_ONLY.json").symlink_to(other)
    with pytest.raises(ValueError, match="unsafe"):
        s.read_reports(tmp_path)


def test_no_patient_records_in_review(three):
    # An unexpectedly added raw field is ignored, not reproduced.
    three["encounter"]["result"]["unexpected_raw_patient_id"] = "SYNTH_PATIENT_001"
    three["procedure"]["result"]["unexpected_raw_encounter_id"] = "SYNTH_ENCOUNTER_002"
    review = s.build_review(three, current_year=2026)
    stext = json.dumps(review)
    assert "SYNTH_PATIENT_001" not in stext
    assert "SYNTH_ENCOUNTER_002" not in stext
    assert review["no_patient_or_encounter_identifiers_returned"] is True
    assert review["final_study_end_year"] is None


def test_main_ack_is_required(monkeypatch):
    with pytest.raises(SystemExit) as ex:
        s.main(["--acknowledge", "NO"])
    assert ex.value.code == 2


def test_empty_but_valid_report_does_not_invent_year(three):
    for key in three:
        obj = three[key]["result"]
        obj["rows_scanned"] = 0
        obj["rows_by_year_bucket_NOT_COVERAGE_VERIFIED"] = {}
        obj["missing_required_values"] = {}
        for field in ("code_system_by_year_bucket_NOT_PERFORMED_PROCEDURES",
                      "encounter_type_by_year_bucket_NOT_INPATIENT_ADMISSIONS",
                      "principal_indicator_by_year_bucket_NOT_VALIDATED",
                      "imaging_code_rows_by_year_NOT_SCANS_OR_PATIENTS"):
            obj[field] = {}
    review = s.build_review(three, current_year=2026)
    assert review["calendar_years_present_NOT_APPROVED"] == []
    assert review["final_study_end_year"] is None
