"""Synthetic-only Step77 patient-capture ceilings and clinical review sheet."""
from copy import deepcopy
import csv
import json

import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step77_pcs_gain_ceiling_and_clinical_review as s77


@pytest.fixture
def data():
    cohort=s62.COHORTS[0]
    base={"patient_cohort_aggregates":{
        "P|"+cohort+"|P=0":{"n":30,"imp":12},
        "P|"+cohort+"|P=1":{"n":20,"imp":4},
    }}
    codeprofile={"source_row_aggregates_LOCAL_ONLY":{
        "2018|0|INDEX_IMP":{
            "source_rows":60,
            "REVIEW_ONLY_potential_neuroimaging_source_rows":6},
        "2018|1|INDEX_IMP":{
            "source_rows":16,
            "REVIEW_ONLY_potential_neuroimaging_source_rows":3},
        "2018|0|NONIMP_DAY0":{
            "source_rows":30,
            "REVIEW_ONLY_potential_neuroimaging_source_rows":0},
        "2018|1|UNIQUE_ED":{
            "source_rows":12,
            "REVIEW_ONLY_potential_neuroimaging_source_rows":2},
    }}
    rows=[
      {"code":"B020ZZZ","family":"B02",
       "modality_candidate":"CNS_CT",
       "FY_titles_for_review":["Computerized Tomography of Brain"],
       "observed_source_service_years":[2018],
       "observed_source_rows_cohort_memberships":6,
       "clinical_reviewer_approval":"PENDING",
       "exact_discharge_date_validity":"NOT_ASSESSED"},
      {"code":"B328ZZZ","family":"B32",
       "modality_candidate":"UPPER_ARTERY_CT",
       "FY_titles_for_review":[
           "Computerized Tomography of Bilateral Internal Carotid Arteries"],
       "observed_source_service_years":[2018],
       "observed_source_rows_cohort_memberships":5,
       "clinical_reviewer_approval":"PENDING",
       "exact_discharge_date_validity":"NOT_ASSESSED"},
    ]
    queue={"review_queue_LOCAL_ONLY":rows}
    return base,codeprofile,queue


def test_upper_bound_is_not_actual_imaging_gain(data):
    b,p,q=data
    rows,by_scope,minimum_gap=s77.analysis(b,p,q,s62.COHORTS[0])
    a1,a0=rows[1],rows[0]
    assert a0["inpatient_CPT14_patients"]==12
    assert a0["CPT14_pct"]==pytest.approx(40)
    assert a0["PCS_index_candidate_source_rows_BOTH_overlapping_cohorts"]==6
    assert a0["MAX_index_CPT14_or_PCS_candidate_pct_UNREALISTIC"]==pytest.approx(60)
    assert a1["inpatient_CPT14_patients"]==4
    assert a1["CPT14_pct"]==pytest.approx(20)
    assert a1["PCS_index_candidate_source_rows_BOTH_overlapping_cohorts"]==3
    assert a1["MAX_index_CPT14_or_PCS_candidate_pct_UNREALISTIC"]==pytest.approx(35)
    assert minimum_gap==pytest.approx(5)
    assert by_scope["INDEX_IMP"]==9
    assert by_scope["UNIQUE_ED"]==2
    assert by_scope["NONIMP_DAY0"]==0


def test_reject_modified_PCS_profile_and_unreviewed_facts(data):
    b,p,q=data
    bad=deepcopy(p)
    bad["source_row_aggregates_LOCAL_ONLY"]["2018|1|INDEX_IMP"][
        "REVIEW_ONLY_potential_neuroimaging_source_rows"]=4
    with pytest.raises(ValueError,match="review inventory"):
        s77.analysis(b,bad,q,s62.COHORTS[0])
    altered=deepcopy(q)
    altered["review_queue_LOCAL_ONLY"][0]["clinical_reviewer_approval"]="APPROVED"
    with pytest.raises(ValueError,match="Unexpected source review"):
        s77.analysis(b,p,altered,s62.COHORTS[0])
    ref=deepcopy(b)
    ref["patient_cohort_aggregates"].pop("P|"+s62.COHORTS[0]+"|P=1")
    with pytest.raises(ValueError,match="missing primary P stratum"):
        s77.analysis(ref,p,q,s62.COHORTS[0])


def test_source_rows_above_population_use_population_ceiling(data):
    b,p,q=data
    bad=deepcopy(p)
    updated=bad["source_row_aggregates_LOCAL_ONLY"]["2018|1|INDEX_IMP"]
    updated["REVIEW_ONLY_potential_neuroimaging_source_rows"]=100
    changed=deepcopy(q)
    changed["review_queue_LOCAL_ONLY"][1][
        "observed_source_rows_cohort_memberships"]=102
    rows,_,_=s77.analysis(b,bad,changed,s62.COHORTS[0])
    assert rows[1]["MAX_new_patients_PCS_INDEX_only_unrealistic"]==16
    assert rows[1]["MAX_index_CPT14_or_PCS_candidate_pct_UNREALISTIC"]==100


def test_review_file_is_pending_private_atomic_and_nonoverwriting(tmp_path,data):
    _,_,q=data
    rows=s77.review_rows(q)
    assert len(rows)==2
    assert set(rows[0])==set(s77.CSV_FIELDS)
    assert all(r["review_include_or_exclude"]=="PENDING" for r in rows)
    assert all(r["FY_discharge_date_validity_checked"]=="NO" for r in rows)
    dest=tmp_path/"clinical_review_LOCAL_ONLY.csv"
    s77.save_review_csv(dest,rows)
    with dest.open(encoding="utf8",newline="") as fh:
        saved=list(csv.DictReader(fh))
    assert len(saved)==2
    assert saved[0]["code"]=="B020ZZZ"
    assert saved[1]["candidate_family"]=="UPPER_ARTERY_CT"
    with pytest.raises(FileExistsError,match="cannot be overwritten"):
        s77.save_review_csv(dest,rows)


def test_console_is_aggregate_only_and_warnings_are_visible(data,capsys):
    b,p,q=data
    rows,by_scope,gap=s77.analysis(b,p,q,s62.COHORTS[0])
    s77.print_summary(rows,by_scope,gap,s62.COHORTS[0],2)
    text=capsys.readouterr().out
    assert "MIN_P0_vs_P1_index_code_capture_gap_pp" in text
    assert "NOT independent validation" in text
    assert "B020ZZZ" not in text
    assert "B328ZZZ" not in text
    assert "patient" in text.lower()


def test_reject_codebook_duplicates_and_incorrect_families(data):
    _,_,q=data
    duplicated=deepcopy(q)
    duplicated["review_queue_LOCAL_ONLY"].append(
        dict(duplicated["review_queue_LOCAL_ONLY"][0]))
    with pytest.raises(ValueError,match="Repeated exact"):
        s77.review_rows(duplicated)
    invalid=deepcopy(q)
    invalid["review_queue_LOCAL_ONLY"][0]["family"]="B32"
    with pytest.raises(ValueError,match="Malformed"):
        s77.review_rows(invalid)
