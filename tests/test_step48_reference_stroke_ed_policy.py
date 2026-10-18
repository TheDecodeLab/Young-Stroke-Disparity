"""No-source-data synthetic tests for Step48 proposed code and episode rules."""
import pytest

from scripts.step48_reference_stroke_ed_policy import (
    CEREBRAL, RETINAL, LEGACY, NONE, stroke_code_family,
    ed_to_ip_candidate, modality_set_names,
)


@pytest.mark.parametrize("system,code,expected", [
    ("ICD-10-CM", "I63.9", CEREBRAL),
    ("ICD-10", "I63.011", CEREBRAL),
    ("ICD-10-CM", "I63.312", CEREBRAL),
    ("ICD-10-CM", "H34.1", RETINAL),
    ("ICD-10-CM", "H34.11", NONE),
    ("ICD-10-CM", "I630", NONE),
    ("ICD-10-CM", "I64", NONE),
    ("ICD-9-CM", "433.01", LEGACY),
    ("ICD-9-CM", "433.11", LEGACY),
    ("ICD-9", "434.01", LEGACY),
    ("ICD-9-CM", "434.11", LEGACY),
    ("ICD-9-CM", "433.00", NONE),
    ("ICD-9-CM", "434.10", NONE),
    ("ICD-10-PCS", "I63.9", NONE),
])
def test_family_is_not_broad_unvalidated_stroke_union(system,code,expected):
    assert stroke_code_family(system,code)==expected


@pytest.fixture
def episode():
    ed={"patient_id":"synthetic_P", "encounter_id":"ED1",
        "type":"EMER", "start_date":"20180514", "end_date":"20180514",
        "verified_site_key":"AUTH_SITE_1"}
    ip={"patient_id":"synthetic_P", "encounter_id":"IP2",
        "type":"IMP","start_date":"20180515","end_date":"20180520",
        "verified_site_key":"AUTH_SITE_1"}
    return ed,ip


def test_separate_encounters_may_form_review_candidate(episode):
    ed,ip=episode
    assert ed_to_ip_candidate(ed,ip)=="candidate_same_site_nearby_ED_IP_REQUIRES_VALIDATION"


def test_site_must_be_verified_not_a_guessed_source_id(episode):
    ed,ip=episode
    ed.pop("verified_site_key")
    ed["source_id"]="SOME_SOURCE"
    ip["source_id"]="SOME_SOURCE"
    assert ed_to_ip_candidate(ed,ip)=="hold_site_mapping_unverified"


def test_cross_patient_and_cross_site_cannot_be_joined(episode):
    ed,ip=episode
    ip["patient_id"]="OTHER"
    assert ed_to_ip_candidate(ed,ip)=="reject_patient_id"
    ip["patient_id"]="synthetic_P"
    ip["verified_site_key"]="OTHER_SITE"
    assert ed_to_ip_candidate(ed,ip)=="hold_different_site_or_transfer"


def test_same_encounter_id_is_not_an_ED_to_IP_bridge(episode):
    ed,ip=episode
    ed["encounter_id"]=ip["encounter_id"]
    assert ed_to_ip_candidate(ed,ip)=="reject_invalid_or_same_encounter_id"


def test_window_is_calendar_days_not_24_hours(episode):
    ed,ip=episode
    ed["start_date"]="20180513"
    ed["end_date"]="20180513"
    assert ed_to_ip_candidate(ed,ip)=="not_adjacent_in_requested_window"
    assert ed_to_ip_candidate(ed,ip,max_gap_days=2)=="candidate_same_site_nearby_ED_IP_REQUIRES_VALIDATION"


def test_emergency_after_admission_is_not_valid(episode):
    ed,ip=episode
    ed["start_date"]="20180516"
    ed["end_date"]="20180516"
    assert ed_to_ip_candidate(ed,ip)=="reject_emergency_starts_after_admission"


def test_missing_and_conflicting_dates_held(episode):
    ed,ip=episode
    ed["start_date"]=""
    assert ed_to_ip_candidate(ed,ip)=="hold_missing_or_invalid_dates"
    ed["start_date"]="20180516"
    ed["end_date"]="20180513"
    assert ed_to_ip_candidate(ed,ip)=="hold_bad_emergency_interval"


def test_overlapping_dates_must_be_reviewed(episode):
    ed,ip=episode
    ed["end_date"]="20180516"
    assert ed_to_ip_candidate(ed,ip)=="hold_overlapping_episode_timing"


def test_wrong_encounter_type_held(episode):
    ed,ip=episode
    ed["type"]="AMB"
    assert ed_to_ip_candidate(ed,ip)=="reject_not_EMER"
    ed["type"]="EMER"
    ip["type"]="AMB"
    assert ed_to_ip_candidate(ed,ip)=="reject_not_IMP"


def test_nonclinical_sensitivity_names_are_not_codebook():
    assert modality_set_names()==(
        "historical_CPT14_anchor_EXPLORATORY",
        "reviewed_CPT_imaging",
        "reviewed_CPT_plus_nonCPT_imaging",
    )
