"""Step52 pure-function synthetic tests; no Research Network clinical file reads."""
from copy import deepcopy

import pytest

from scripts.step49_ed_ip_episode_candidates import pair_candidate
from scripts.step52_date_only_ed_ip_sensitivity import (
    DATE_ONLY_PAIR, DATE_ONLY_UNIQUE, date_only_pair_candidate,
    resolve_date_only_candidates, date_only_window_summary,
    outcome_definition_labels, investigator_analysis_contract,
)


@pytest.fixture
def records():
    ed = {"patient_id": "SYNTH_P", "encounter_id": "ED1",
          "type": "EMER", "start_date": "20181229", "end_date": "20181231",
          "source_id": "UNKNOWN_SOURCE_1"}
    ip = {"patient_id": "SYNTH_P", "encounter_id": "IP1",
          "type": "IMP", "start_date": "20190101", "end_date": "20190104",
          "source_id": "UNKNOWN_SOURCE_2"}
    return ed, ip


def test_site_aware_rule_stays_strict_but_date_only_rule_is_available(records):
    ed,ip=records
    assert pair_candidate(ed, ip) == "hold_site_mapping_unverified"
    assert date_only_pair_candidate(ed,ip) == DATE_ONLY_PAIR


def test_no_same_hospital_claim_even_with_one_candidate(records):
    ed,ip=records
    result=resolve_date_only_candidates([ed],[ip])
    assert result[("SYNTH_P","IP1")] == {
        "status": DATE_ONLY_UNIQUE,
        "emergency_key": ("SYNTH_P","ED1"),
        "calendar_gap_days": 1,
        "same_hospital_verified": False,
    }


def test_source_id_never_changes_date_only_decision(records):
    ed,ip=records
    result=date_only_pair_candidate(ed,ip)
    assert result==DATE_ONLY_PAIR
    ip["source_id"]=ed["source_id"]
    assert date_only_pair_candidate(ed,ip)==result
    ed["source_id"]="CHANGED"
    assert date_only_pair_candidate(ed,ip)==result


@pytest.mark.parametrize("days,expected",[(0,False),(1,True),(2,True)])
def test_gap_windows_use_ED_end_date_not_start(records,days,expected):
    ed,ip=records
    status=date_only_pair_candidate(ed,ip,days)
    assert (status==DATE_ONLY_PAIR)==expected


def test_same_day_is_candidate_not_verified_episode(records):
    ed,ip=records
    ed["end_date"]="20190101"
    assert date_only_pair_candidate(ed,ip,0)==DATE_ONLY_PAIR
    result=resolve_date_only_candidates([ed],[ip],0)
    assert result[("SYNTH_P","IP1")]["same_hospital_verified"] is False


def test_long_ED_stay_can_end_day_before_admission(records):
    ed,ip=records
    ed["start_date"]="20181225"
    assert date_only_pair_candidate(ed,ip)==DATE_ONLY_PAIR


def test_two_ed_visits_remain_ambiguous_not_greedily_assigned(records):
    ed,ip=records
    ed2={**ed,"encounter_id":"ED2","start_date":"20181230"}
    result=resolve_date_only_candidates([ed,ed2],[ip])
    assert result[("SYNTH_P","IP1")]["status"]=="ambiguous_multiple_ED_candidates"
    assert result[("SYNTH_P","IP1")]["emergency_key"] is None


def test_one_ed_and_two_admissions_remain_ambiguous(records):
    ed,ip=records
    ip2={**ip,"encounter_id":"IP2","start_date":"20181231"}
    result=resolve_date_only_candidates([ed],[ip,ip2])
    assert result[("SYNTH_P","IP1")]["status"]=="ambiguous_one_ED_multiple_IP"
    assert result[("SYNTH_P","IP2")]["status"]=="ambiguous_one_ED_multiple_IP"


def test_missing_end_date_competitor_blocks_otherwise_unique(records):
    ed,ip=records
    other={**ed,"encounter_id":"MISSING_ED","end_date":""}
    result=resolve_date_only_candidates([ed,other],[ip])
    assert result[("SYNTH_P","IP1")]["status"]=="hold_unresolved_possible_ED"


def test_known_cross_site_disagreement_is_not_linked(records):
    ed,ip=records
    ed["verified_site_key"]="HOSPITAL_A"
    ip["verified_site_key"]="HOSPITAL_B"
    assert date_only_pair_candidate(ed,ip)=="hold_different_site_or_transfer"
    result=resolve_date_only_candidates([ed],[ip])
    assert result[("SYNTH_P","IP1")]["status"]=="hold_unresolved_possible_ED"


def test_cross_patient_matches_are_rejected(records):
    ed,ip=records
    ip["patient_id"]="OTHER"
    assert date_only_pair_candidate(ed,ip)=="reject_patient_id"
    assert resolve_date_only_candidates([ed],[ip])[("OTHER","IP1")]["status"]=="no_unique_date_only_ED_candidate"


def test_duplicate_keys_block_date_only_links(records):
    ed,ip=records
    result=resolve_date_only_candidates([ed,deepcopy(ed)],[ip])
    assert result[("SYNTH_P","IP1")]["status"]=="hold_duplicate_patient_encounter_key"


def test_cross_patient_collision_in_encounter_id_blocks(records):
    ed,ip=records
    second={**ed,"patient_id":"OTHER"}
    result=resolve_date_only_candidates([ed,second],[ip])
    assert result[("SYNTH_P","IP1")]["status"]=="hold_encounter_id_reused_across_patients"


@pytest.mark.parametrize("edchange,expected",[
    ({"end_date":""},"hold_missing_ED_end_date"),
    ({"end_date":"20181301"},"hold_missing_or_invalid_dates"),
    ({"start_date":"20190102","end_date":"20190102"},"reject_emergency_starts_after_admission"),
    ({"end_date":"20190102"},"hold_overlapping_episode_timing"),
])
def test_unusable_date_patterns_are_not_links(records,edchange,expected):
    ed,ip=records
    ed.update(edchange)
    assert date_only_pair_candidate(ed,ip)==expected


def test_no_ED_visit_preserves_inpatient_entry(records):
    _,ip=records
    report=resolve_date_only_candidates([],[ip])
    assert report[("SYNTH_P","IP1")]["status"]=="no_unique_date_only_ED_candidate"


def test_in_memory_aggregate_reports_never_show_patient_or_encounter_ids(records):
    ed,ip=records
    a=date_only_window_summary([ed],[ip])
    assert a["0"]["unique_date_only_provisional_candidates"]==0
    assert a["1"]["unique_date_only_provisional_candidates"]==1
    assert a["2"]["provisional_gap_days_counts"]=={1:1}
    assert a["1"]["same_hospital_verified"] is False
    assert a["1"]["patient_id_cross_hco_scope_verified"] is False
    assert "SYNTH_P" not in str(a)
    assert "ED1" not in str(a)
    assert "IP1" not in str(a)


def test_no_mutation_of_input_dictionaries(records):
    ed,ip=records
    originals=deepcopy((ed,ip))
    date_only_window_summary([ed],[ip])
    assert originals==(ed,ip)


@pytest.mark.parametrize("bad",[-1,4,True,1.2,"1",None])
def test_invalid_link_window_fails_closed(records,bad):
    ed,ip=records
    with pytest.raises(ValueError):
        date_only_pair_candidate(ed,ip,bad)


def test_input_type_rejected(records):
    _,ip=records
    with pytest.raises(TypeError):
        resolve_date_only_candidates(["not a dictionary"],[ip])


def test_report_labels_never_claim_verified_hospital_episode():
    labels=outcome_definition_labels()
    assert "REFERENCE" in labels[0]
    assert "PROVISIONAL_SENSITIVITY" in labels[1]
    assert not any("CONFIRMED" in label for label in labels)


def test_investigator_freeze_primary_is_same_inpatient_encounter_only():
    contract = investigator_analysis_contract()
    assert contract["primary"]["key"] == "A_same_IMP_encounter"
    assert contract["primary"]["role"] == "primary"
    assert contract["primary"]["procedure_encounter_types"] == ("IMP",)
    assert contract["primary"]["may_include_separate_ED_encounter"] is False
    assert "PRIMARY_REFERENCE" in outcome_definition_labels()[0]


def test_ED_inclusion_is_sensitivity_only_with_bidirectional_uniqueness():
    contract = investigator_analysis_contract()
    sensitivity = contract["sensitivity"]
    assert sensitivity["role"] == "sensitivity"
    assert sensitivity["procedure_encounter_types"] == ("IMP", "EMER")
    assert sensitivity["ED_linkage_requires_reciprocal_uniqueness"] is True
    assert sensitivity["ED_to_IP_main_gap_calendar_days"] == (0, 1)
    assert sensitivity["ED_to_IP_window_sensitivity_max_gap_days"] == (0, 1, 2)
    assert sensitivity["same_hospital_verified"] is False


def test_same_policy_in_both_primary_age_cohorts_without_relabelling():
    contract = investigator_analysis_contract()
    assert contract["co_primary_age_cohorts"] == (
        "uniform_18_50", "original_sex_specific_18_52_54"
    )
    assert contract["denominator_selected_independent_of_imaging"] is True
    assert contract["study_outcome"] == "documented_imaging_codes_not_confirmed_receipt"


def test_investigator_method_choice_cannot_authorize_clinical_scan():
    contract = investigator_analysis_contract()
    assert contract["clinical_codebook_review_complete"] is False
    assert contract["institutional_full_scan_authorized_by_this_decision"] is False
