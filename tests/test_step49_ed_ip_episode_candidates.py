"""Step49 synthetic-only date-end-first ED-to-IP candidate quality tests.

Only in-memory invented encounter dictionaries. No TriNetX ZIP, no SQLite,
no patient-level file output, no source scans or network access.
"""
from copy import deepcopy

import pytest

from scripts.step48_reference_stroke_ed_policy import ed_to_ip_candidate
from scripts.step49_ed_ip_episode_candidates import (
    CANDIDATE, EPISODE_CANDIDATE, pair_candidate, resolve_episode_candidates,
    compare_link_windows,
)


@pytest.fixture
def pair():
    ed = {
        "patient_id": "TEST_PATIENT", "encounter_id": "ED_1",
        "type": "EMER", "start_date": "20181228", "end_date": "20181231",
        "verified_site_key": "TEST_AUTH_SITE_A",
    }
    ip = {
        "patient_id": "TEST_PATIENT", "encounter_id": "IP_1",
        "type": "IMP", "start_date": "20190101", "end_date": "20190106",
        "verified_site_key": "TEST_AUTH_SITE_A",
    }
    return ed, ip


def test_long_ED_stay_uses_ED_end_not_start(pair):
    ed, ip = pair
    assert (ip["start_date"], ed["start_date"]) == ("20190101","20181228")
    assert pair_candidate(ed, ip, 1) == CANDIDATE
    assert ed_to_ip_candidate(ed, ip, 1) == CANDIDATE
    assert pair_candidate(ed, ip, 0) == "not_adjacent_in_requested_window"


def test_same_day_and_next_day_and_two_day_windows(pair):
    ed, ip = pair
    ed["end_date"] = "20190101"
    assert pair_candidate(ed, ip, 0) == CANDIDATE
    ed["end_date"] = "20181231"
    assert pair_candidate(ed, ip, 0) == "not_adjacent_in_requested_window"
    assert pair_candidate(ed, ip, 1) == CANDIDATE
    ed["end_date"] = "20181230"
    assert pair_candidate(ed, ip, 1) == "not_adjacent_in_requested_window"
    assert pair_candidate(ed, ip, 2) == CANDIDATE
    assert pair_candidate(ed, ip, 3) == CANDIDATE


def test_missing_ED_end_blocks_even_if_ED_start_is_near_IP(pair):
    ed, ip = pair
    ed["start_date"] = "20181231"
    ed.pop("end_date")
    assert pair_candidate(ed, ip, 1) == "hold_missing_ED_end_date"


@pytest.mark.parametrize("bad_end", ["20190230", "junk", "20181301"])
def test_malformed_ED_end_blocks(pair, bad_end):
    ed, ip = pair
    ed["end_date"] = bad_end
    assert pair_candidate(ed, ip) == "hold_missing_or_invalid_dates"


def test_ed_start_after_admission_rejected(pair):
    ed, ip = pair
    ed["start_date"] = "20190102"
    ed["end_date"] = "20190102"
    assert pair_candidate(ed, ip) == "reject_emergency_starts_after_admission"


def test_intervals_that_end_after_admission_are_held(pair):
    ed, ip = pair
    ed["end_date"] = "20190102"
    assert pair_candidate(ed, ip) == "hold_overlapping_episode_timing"


def test_same_day_overlap_without_hours_is_provisional(pair):
    ed, ip = pair
    ed["end_date"] = "20190101"
    assert pair_candidate(ed, ip, 0) == CANDIDATE
    # Day precision alone does not demonstrate chronological transfer.


def test_inpatient_bad_end_date_held(pair):
    ed, ip = pair
    ip["end_date"] = "20181231"
    assert pair_candidate(ed, ip) == "hold_bad_inpatient_interval"


def test_missing_or_unverified_site_is_not_imputed_from_source_id(pair):
    ed, ip = pair
    ed.pop("verified_site_key")
    ed["source_id"] = "source_12"
    ip["source_id"] = "source_12"
    assert pair_candidate(ed, ip) == "hold_site_mapping_unverified"


def test_different_site_is_not_auto_connected(pair):
    ed, ip = pair
    ed["verified_site_key"] = "SITE_B"
    assert pair_candidate(ed, ip) == "hold_different_site_or_transfer"


def test_unique_candidate_always_stays_provisional(pair):
    ed, ip = pair
    records = resolve_episode_candidates([ed], [ip])
    link = records[("TEST_PATIENT","IP_1")]
    assert link == {
        "status": EPISODE_CANDIDATE,
        "emergency_key": ("TEST_PATIENT","ED_1"),
        "calendar_gap_days": 1,
    }


def test_two_ED_encounters_competing_for_one_IP_are_not_autolinked(pair):
    ed, ip = pair
    second = {**ed, "encounter_id": "ED_2", "start_date": "20181231"}
    links = resolve_episode_candidates([ed, second], [ip])
    assert links[("TEST_PATIENT","IP_1")]["status"] == "ambiguous_multiple_ED_candidates"
    assert links[("TEST_PATIENT","IP_1")]["emergency_key"] is None


def test_one_ED_competing_for_two_IP_is_not_autolinked(pair):
    ed, ip = pair
    second = {**ip, "encounter_id": "IP_2", "start_date": "20181231"}
    links = resolve_episode_candidates([ed],[ip,second],max_gap_days=1)
    assert links[("TEST_PATIENT","IP_1")]["status"] == "ambiguous_one_ED_multiple_IP"
    assert links[("TEST_PATIENT","IP_2")]["status"] == "ambiguous_one_ED_multiple_IP"


def test_duplicate_encounter_rows_block_even_if_identical(pair):
    ed, ip = pair
    links = resolve_episode_candidates([ed,deepcopy(ed)],[ip])
    assert links[("TEST_PATIENT","IP_1")]["status"] == "hold_duplicate_patient_encounter_key"


def test_duplicate_IP_key_blocks(pair):
    ed, ip = pair
    links = resolve_episode_candidates([ed], [ip, deepcopy(ip)])
    assert links[("TEST_PATIENT","IP_1")]["status"] == "hold_duplicate_patient_encounter_key"


def test_unknown_site_competitor_blocks_the_otherwise_unique_match(pair):
    ed, ip = pair
    second = {**ed, "encounter_id": "ED_UNKNOWN_SITE"}
    second.pop("verified_site_key")
    links = resolve_episode_candidates([ed,second],[ip])
    assert links[("TEST_PATIENT","IP_1")]["status"] == "hold_unresolved_potential_ED_competitor"


def test_unresolved_missing_end_competitor_blocks_link(pair):
    ed, ip = pair
    second = {**ed, "encounter_id": "ED_MISSING_END"}
    second.pop("end_date")
    links = resolve_episode_candidates([ed,second],[ip])
    assert links[("TEST_PATIENT","IP_1")]["status"] == "hold_unresolved_potential_ED_competitor"


def test_wrong_person_never_linked_even_if_dates_match(pair):
    ed, ip = pair
    ed["patient_id"] = "OTHER_PATIENT"
    links=resolve_episode_candidates([ed],[ip])
    assert links[("TEST_PATIENT","IP_1")]["status"] == "no_unique_ED_candidate"


def test_window_comparison_counts_and_calendar_days(pair):
    ed, ip = pair
    report = compare_link_windows([ed],[ip])
    assert list(report) == ["0", "1", "2"]
    assert report["0"]["unique_provisional_links"] == 0
    assert report["1"]["unique_provisional_links"] == 1
    assert report["2"]["candidate_end_to_start_gap_days"] == {1:1}
    assert report["1"]["clinical_episode_linkage_validated"] is False
    assert all("TEST_PATIENT" not in str(v) for v in report.values())


def test_no_raw_identifiers_appear_in_window_summary(pair):
    ed, ip = pair
    report=compare_link_windows([ed],[ip],windows=[0,1,2])
    assert "TEST_PATIENT" not in str(report)
    assert "ED_1" not in str(report)
    assert "IP_1" not in str(report)


def test_no_mutation_of_synthetic_input(pair):
    ed, ip = pair
    before=deepcopy((ed,ip))
    resolve_episode_candidates([ed],[ip],1)
    assert (ed,ip)==before


@pytest.mark.parametrize("value",[-1, 4, 1.0, "1", None, True])
def test_invalid_window_rejected(pair,value):
    ed, ip = pair
    with pytest.raises(ValueError):
        pair_candidate(ed,ip,max_gap_days=value)


def test_represent_all_IP_even_without_ED():
    ip={"patient_id":"TEST_PATIENT","encounter_id":"IP_9","type":"IMP",
        "start_date":"20180101","end_date":"20180104","verified_site_key":"SITE_A"}
    links=resolve_episode_candidates([], [ip])
    assert links[("TEST_PATIENT","IP_9")]["status"] == "no_unique_ED_candidate"



def test_same_encounter_identifier_reused_across_patients_is_held(pair):
    ed, ip = pair
    other_patient_ED={**ed, "patient_id":"OTHER_PERSON"}
    results=resolve_episode_candidates([ed,other_patient_ED], [ip])
    assert results[("TEST_PATIENT","IP_1")]["status"]=="hold_encounter_id_reused_across_patients"


def test_cross_site_transfer_competitor_prevents_unique_assignment(pair):
    ed, ip = pair
    different_site_ED={**ed, "encounter_id":"ED_POSSIBLE_TRANSFER",
                       "verified_site_key":"DIFFERENT_HOSPITAL"}
    results=resolve_episode_candidates([ed,different_site_ED],[ip])
    assert results[("TEST_PATIENT","IP_1")]["status"]=="hold_unresolved_potential_ED_competitor"


def test_patient_ID_matches_but_missing_site_never_links(pair):
    ed,ip=pair
    ip.pop("verified_site_key")
    result=resolve_episode_candidates([ed],[ip])
    assert result[("TEST_PATIENT","IP_1")]["status"]=="hold_unresolved_potential_ED_competitor"
