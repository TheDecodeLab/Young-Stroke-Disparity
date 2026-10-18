"""Step53 synthetic-only outcome assembly tests; no clinical source access."""
from copy import deepcopy

import pytest

from scripts.step53_outcome_reference_assembler import (
    assemble_outcome_reference, CATEGORIES, WINDOWS,
)


@pytest.fixture
def scenario():
    patient = "SYNTHETIC_STROKE_PERSON"
    ip = {"patient_id": patient, "encounter_id": "IP11",
          "type": "IMP", "start_date": "20190101",
          "end_date": "20190104"}
    ed = {"patient_id": patient, "encounter_id": "ED10",
          "type": "EMER", "start_date": "20181229",
          "end_date": "20181231"}
    index = {"cohort": "uniform_18_50", "patient_id": patient,
             "encounter_id": "IP11", "start_date": "20190101"}
    procedures = [
        {"patient_id": patient, "encounter_id": "IP11",
         "date": "20190102", "category": "MRI_BRAIN",
         "codebook_reviewed_performed": True},
        {"patient_id": patient, "encounter_id": "ED10",
         "date": "20181231", "category": "CTA_HEAD",
         "codebook_reviewed_performed": True},
    ]
    return index, ip, ed, procedures


def rows(scenario, *, index=None, ip=None, ed=None, procedures=None,
         all_inpatient=None, all_emergency=None):
    ix, i, e, p = scenario
    x = [ix if index is None else index]
    return assemble_outcome_reference(
        x,
        [i if ip is None else ip] if all_inpatient is None else all_inpatient,
        [e if ed is None else ed] if all_emergency is None else all_emergency,
        p if procedures is None else procedures,
    )


def take(result):
    return result[("uniform_18_50", "SYNTHETIC_STROKE_PERSON")]


def test_ED_event_is_never_primary_even_when_one_day_before_admission(scenario):
    item=take(rows(scenario))
    assert item["primary_assessable"] is True
    assert item["primary_recorded_modalities"] == ("MRI_BRAIN",)
    for days in WINDOWS:
        assert "CTA_HEAD" not in item["primary_recorded_modalities"]


def test_main_sensitivity_counts_uniquely_linked_ED_imaging_only(scenario):
    item=take(rows(scenario))
    assert item["date_only_ED_sensitivity_by_max_gap"][0]["recorded_modalities"] == ("MRI_BRAIN",)
    assert item["date_only_ED_sensitivity_by_max_gap"][1]["recorded_modalities"] == ("CTA_HEAD","MRI_BRAIN")
    assert item["date_only_ED_sensitivity_by_max_gap"][2]["recorded_modalities"] == ("CTA_HEAD","MRI_BRAIN")
    assert item["date_only_ED_sensitivity_by_max_gap"][1]["provisional_ED_used"] is True
    assert item["date_only_ED_sensitivity_by_max_gap"][1]["same_hospital_verified"] is False


def test_no_imaging_event_does_not_change_preselected_denominator(scenario):
    item=take(rows(scenario,procedures=[]))
    assert item["primary_recorded_modalities"] == ()
    assert item["denominator_from_preselected_index_not_imaging"] is True
    assert item["primary_assessable"] is True


def test_duplicate_procedures_do_not_double_count_a_modality(scenario):
    index,ip,ed,p=scenario
    item=take(rows(scenario,procedures=p+p))
    assert item["primary_recorded_modalities"] == ("MRI_BRAIN",)
    assert item["date_only_ED_sensitivity_by_max_gap"][1]["recorded_modalities"] == ("CTA_HEAD","MRI_BRAIN")


def test_outside_interval_procedures_do_not_count(scenario):
    index,ip,ed,p=scenario
    invalid_inpatient={**p[0],"date":"20190108"}
    invalid_ed={**p[1],"date":"20190102"}
    item=take(rows(scenario,procedures=[invalid_inpatient,invalid_ed]))
    assert item["primary_recorded_modalities"] == ()
    assert item["date_only_ED_sensitivity_by_max_gap"][1]["recorded_modalities"] == ()


def test_other_patient_and_other_encounter_event_not_counted(scenario):
    index,ip,ed,p=scenario
    other_patient={**p[0],"patient_id":"OTHER_PERSON"}
    other_encounter={**p[1],"encounter_id":"ED_ELSEWHERE"}
    item=take(rows(scenario,procedures=[other_patient,other_encounter]))
    assert item["primary_recorded_modalities"] == ()
    assert item["date_only_ED_sensitivity_by_max_gap"][1]["recorded_modalities"] == ()


def test_multiple_ED_candidates_prevent_sensitivity_ED_inclusion(scenario):
    index,ip,ed,p=scenario
    ed2={**ed,"encounter_id":"ED_COMPETING","start_date":"20181231"}
    item=take(rows(scenario,all_emergency=[ed,ed2]))
    assert item["primary_recorded_modalities"] == ("MRI_BRAIN",)
    b=item["date_only_ED_sensitivity_by_max_gap"][1]
    assert b["provisional_ED_used"] is False
    assert b["candidate_link_status"]=="ambiguous_multiple_ED_candidates"
    assert b["recorded_modalities"]==("MRI_BRAIN",)


def test_competing_NONINDEX_inpatient_blocks_ED_association(scenario):
    index,ip,ed,p=scenario
    competing={**ip,"encounter_id":"NONINDEX_IP","start_date":"20181231",
               "end_date":"20190103"}
    item=take(rows(scenario,all_inpatient=[ip,competing]))
    b=item["date_only_ED_sensitivity_by_max_gap"][1]
    assert b["candidate_link_status"]=="ambiguous_one_ED_multiple_IP"
    assert b["provisional_ED_used"] is False


def test_same_patient_in_two_age_cohorts_gets_separate_rows(scenario):
    index,ip,ed,p=scenario
    second={**index,"cohort":"original_sex_specific_18_52_54"}
    result=assemble_outcome_reference([index,second],[ip],[ed],p)
    assert len(result)==2
    assert result[("uniform_18_50",index["patient_id"])]["primary_recorded_modalities"]==(
        "MRI_BRAIN",
    )
    assert result[("original_sex_specific_18_52_54",index["patient_id"])]["primary_recorded_modalities"]==(
        "MRI_BRAIN",
    )


def test_incomplete_IP_stay_is_not_falsely_called_no_imaging(scenario):
    index,ip,ed,p=scenario
    ip={**ip,"end_date":""}
    item=take(rows(scenario,ip=ip))
    assert item["primary_assessable"] is False
    assert item["primary_recorded_modalities"]==()
    assert all(not row["provisional_ED_used"]
               for row in item["date_only_ED_sensitivity_by_max_gap"].values())


def test_unreviewed_codebook_event_is_rejected(scenario):
    index,ip,ed,p=scenario
    unreviewed={**p[0],"codebook_reviewed_performed":False}
    with pytest.raises(ValueError,match="reviewed-performed"):
        rows(scenario,procedures=[unreviewed])


def test_missing_codebook_status_is_rejected(scenario):
    index,ip,ed,p=scenario
    unreviewed=dict(p[0])
    unreviewed.pop("codebook_reviewed_performed")
    with pytest.raises(ValueError,match="reviewed-performed"):
        rows(scenario,procedures=[unreviewed])


def test_invalid_or_unexpected_modality_rejected(scenario):
    index,ip,ed,p=scenario
    event={**p[0],"category":"ANY_UNKNOWN_IMAGING"}
    with pytest.raises(ValueError,match="category"):
        rows(scenario,procedures=[event])
    assert len(CATEGORIES)==6


def test_unvalidated_index_definition_rejected(scenario):
    index,ip,ed,p=scenario
    bad_index={**index,"cohort":"a_new_primary_definition"}
    with pytest.raises(ValueError,match="co-primary"):
        rows(scenario,index=bad_index)


def test_index_must_match_an_inpatient_record(scenario):
    index,ip,ed,p=scenario
    invalid={**index,"encounter_id":"WRONG_IP"}
    with pytest.raises(ValueError,match="index"):
        rows(scenario,index=invalid)


def test_index_start_date_cannot_disagree_with_visit(scenario):
    index,ip,ed,p=scenario
    invalid={**index,"start_date":"20190103"}
    with pytest.raises(ValueError,match="start disagrees"):
        rows(scenario,index=invalid)


def test_duplicate_index_within_one_cohort_is_rejected(scenario):
    index,ip,ed,p=scenario
    with pytest.raises(ValueError,match="Duplicate patient index"):
        assemble_outcome_reference([index,index],[ip],[ed],p)


def test_duplicate_ip_record_rejected(scenario):
    index,ip,ed,p=scenario
    with pytest.raises(ValueError,match="duplicated"):
        assemble_outcome_reference([index],[ip,deepcopy(ip)],[ed],p)


def test_shared_ED_and_IP_encounter_key_rejected(scenario):
    index,ip,ed,p=scenario
    merged={**ed,"encounter_id":ip["encounter_id"]}
    with pytest.raises(ValueError,match="both IMP and EMER"):
        rows(scenario,ed=merged)


def test_source_id_does_not_influence_primary_or_sensitivity(scenario):
    index,ip,ed,p=scenario
    old=rows(scenario)
    new_ed={**ed,"source_id":"CHANGED_SOURCE"}
    new_ip={**ip,"source_id":"CHANGED_SOURCE"}
    new=rows(scenario,ed=new_ed,ip=new_ip)
    assert old==new


def test_input_not_mutated(scenario):
    prior=deepcopy(scenario)
    rows(scenario)
    assert scenario==prior


def test_date_window_not_necessarily_monotonic_due_to_ambiguity(scenario):
    index,ip,ed,p=scenario
    extra={**ed,"encounter_id":"ED_GAP_2","start_date":"20181229",
           "end_date":"20181230"}
    item=take(rows(scenario,all_emergency=[ed,extra]))
    day1=item["date_only_ED_sensitivity_by_max_gap"][1]
    day2=item["date_only_ED_sensitivity_by_max_gap"][2]
    assert day1["provisional_ED_used"] is True
    assert day2["candidate_link_status"]=="ambiguous_multiple_ED_candidates"
    assert day2["provisional_ED_used"] is False
