"""Synthetic Step60-shaped data only; never access TriNetX or private reports."""
import copy
import json
import os
import stat
from pathlib import Path
import pytest
from scripts import step61_disclosure_candidate as q


def stage_data(e=2000, d=2600, p=3000, cpt=1700, core=120):
    assert cpt <= p
    return {
        "encounter": {"source_rows": e, "IMP": e // 2, "EMER": e // 2},
        "diagnosis": {"source_rows": d, "ICD-10-CM": d},
        "procedure": {"source_rows": p, "CPT": cpt, "SNOMED": p-cpt,
                      "CPT14_CODE_ROWS_NOT_EXAMS": core,
                      "COMBINED_CTA_70471_CANDIDATE_ROWS": 0,
                      "CT_PERFUSION_SEPARATE_ROWS": 0},
    }


def fake_report():
    return {
        "stage": "STEP60_LOCAL_PRIVATE_STEP59_REVIEW",
        "source": "THREE_EXISTING_STEP59_PRIVATE_REPORTS_ONLY",
        "all_three_step59_artifacts_validated": True,
        "no_source_clinical_rows_read": True,
        "no_patient_or_encounter_identifiers_returned": True,
        "sharing_requires_disclosure_review": True,
        "final_study_end_year": None,
        "private_table_row_counts_NOT_PATIENTS": {
            "encounter": 4100, "diagnosis": 5300, "procedure": 6500,
        },
        "private_year_by_table_NOT_SITE_ADJUSTED": {
            "2023": stage_data(),
            "2024": stage_data(2100,2700,3500,2500,500),
        },
        "automated_review_flags_NOT_CLINICAL_SIGNOFF": {
            "CPT_rare_sensitive": "SYNTH_ID_abc",
            "site_note": "SYNTH_PRIVATE_HOSPITAL_NAME"
        },
        "private_table_totally_unrelated": {"patient_id": "SYNTH_SECRET_P12345"},
    }


def test_no_counts_or_sensitive_strings_are_emitted():
    output = q.summarize(fake_report(), current_year=2026)
    content = json.dumps(output)
    for value in ("SYNTH_ID_abc", "SYNTH_PRIVATE_HOSPITAL_NAME",
                  "SYNTH_SECRET_P12345", "4100", "5300", "6500", "1700", "2500"):
        assert value not in content
    assert "source_rows" not in content
    assert output["clinical_record_or_patient_counts_included"] is False
    assert output["exact_source_row_counts_included"] is False
    assert output["exact_rates_or_percentages_included"] is False
    assert output["study_end_year_selected"] is False
    assert output["disclosure_status"] == "NOT_APPROVED_BY_SCRIPT_USER_MUST_REVIEW"


def test_year_trends_and_mix_are_only_coarse():
    result = q.summarize(fake_report(), current_year=2026)
    rows = result["provisional_coarse_year_summary"]
    assert [x["calendar_year_observed_NOT_completeness_approved"] for x in rows] == ["2023","2024"]
    assert rows[0]["year_to_previous_adjacent_released_year_row_volume_pattern"] == "not_available"
    assert rows[1]["year_to_previous_adjacent_released_year_row_volume_pattern"]["encounter"] == "roughly_similar"
    assert rows[0]["procedure_CPT_vs_other_systems"] == "mixed_CPT_and_non_CPT"
    assert rows[1]["procedure_CPT_vs_other_systems"] == "mostly_CPT"
    assert rows[0]["core_CPT14_qualitative_signal"] == "recorded_core_CPT_codes_present_in_large_aggregate_NOT_scans"


def test_whole_year_suppressed_if_any_stage_below_denominator():
    r=fake_report()
    r["private_year_by_table_NOT_SITE_ADJUSTED"]["2024"]["diagnosis"]["source_rows"] = 999
    out=q.summarize(r,current_year=2026)
    assert len(out["provisional_coarse_year_summary"]) == 1
    assert out["provisional_coarse_year_summary"][0]["calendar_year_observed_NOT_completeness_approved"] == "2023"


def test_contrast_suppression_is_not_reported_as_absence():
    r=fake_report()
    p=r["private_year_by_table_NOT_SITE_ADJUSTED"]["2023"]["procedure"]
    p["CPT"] = p["source_rows"]-10
    p["SNOMED"] = 10
    p["CPT14_CODE_ROWS_NOT_EXAMS"] = 1
    out=q.summarize(r,current_year=2026)
    first=out["provisional_coarse_year_summary"][0]
    assert first["procedure_CPT_vs_other_systems"]=="withheld"
    assert first["core_CPT14_qualitative_signal"]=="withheld_not_evidence_of_absence"


def test_absent_code_not_proven_when_cpt14_zero():
    r=fake_report()
    r["private_year_by_table_NOT_SITE_ADJUSTED"]["2023"]["procedure"]["CPT14_CODE_ROWS_NOT_EXAMS"] = 0
    out=q.summarize(r,2026)
    assert out["provisional_coarse_year_summary"][0]["core_CPT14_qualitative_signal"]=="withheld_not_evidence_of_absence"


def test_suppressed_gap_does_not_compare_nonadjacent_years():
    r=fake_report()
    r["private_table_row_counts_NOT_PATIENTS"]={"encounter":12000,"diagnosis":12000,"procedure":12000}
    r["private_year_by_table_NOT_SITE_ADJUSTED"]["2025"]=stage_data(10,2000,3000,1700,120)
    r["private_year_by_table_NOT_SITE_ADJUSTED"]["2026"]=stage_data(2000,2100,2200,1100,120)
    out=q.summarize(r,2026)
    rows=out["provisional_coarse_year_summary"]
    assert [x["calendar_year_observed_NOT_completeness_approved"] for x in rows] == ["2023","2024","2026"]
    assert rows[-1]["year_to_previous_adjacent_released_year_row_volume_pattern"] == "not_available"
    assert rows[-1]["current_calendar_year_can_be_partial"] is True


def test_fail_closed_on_provenance_or_anomalous_data():
    for change in (
        lambda r: r.update({"sharing_requires_disclosure_review": False}),
        lambda r: r.update({"final_study_end_year": 2024}),
        lambda r: r.update({"all_three_step59_artifacts_validated": False}),
        lambda r: r["private_table_row_counts_NOT_PATIENTS"].update({"procedure":-1}),
        lambda r: r["private_year_by_table_NOT_SITE_ADJUSTED"]["2023"]["procedure"].update({"CPT":99999}),
        lambda r: r["private_year_by_table_NOT_SITE_ADJUSTED"]["2023"]["procedure"].update({"source_rows":True}),
        lambda r: r["private_year_by_table_NOT_SITE_ADJUSTED"].update({"2001":stage_data()}),
        lambda r: r["private_year_by_table_NOT_SITE_ADJUSTED"]["2023"].pop("diagnosis"),
    ):
        r=fake_report()
        change(r)
        with pytest.raises(ValueError):
            q.summarize(r,2026)


def test_separately_rejects_false_permission():
    with pytest.raises(SystemExit) as er:
        q.main(["--acknowledge","WRONG"])
    assert er.value.code==2


def test_private_file_permissions_no_overwrite_and_path_restriction(tmp_path):
    folder=tmp_path/"private"
    folder.mkdir(mode=0o700)
    dest=folder/"candidate.json"
    candidate=q.summarize(fake_report(),2026)
    q.write_private(candidate,dest,folder)
    assert stat.S_IMODE(dest.stat().st_mode)==0o600
    with pytest.raises(FileExistsError):
        q.write_private(candidate,dest,folder)
    with pytest.raises(ValueError):
        q.write_private(candidate,tmp_path/"insecure.json",folder)
    assert json.loads(dest.read_text())==candidate


def test_input_size_symlink_rejected(tmp_path):
    source=tmp_path/"private.json"
    source.write_text(json.dumps(fake_report()))
    assert q.read_private(source)["stage"]=="STEP60_LOCAL_PRIVATE_STEP59_REVIEW"
    link=tmp_path/"link.json"
    link.symlink_to(source)
    with pytest.raises(ValueError):
        q.read_private(link)


def test_no_raw_source_csv_or_step59_files_are_referenced():
    source = Path(q.__file__).read_text()
    assert 'zipfile' not in source
    assert 'step59_encounter_LOCAL_ONLY.json' not in source
    assert 'step59_procedure_LOCAL_ONLY.json' not in source
    assert 'step59_diagnosis_LOCAL_ONLY.json' not in source
