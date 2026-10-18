"""Synthetic-only Research Network pre-reconstruction evidence gate tests."""
import pytest
from scripts import research_network_pre_reconstruction_gate as gate


def _item(status="confirmed_external", evidence="REFERENCE_SYNTHETIC", role="data_steward"):
    return {"status": status, "evidence_ref": evidence, "reviewer_role": role}


def _full_packet():
    return {key: _item() for key in gate.REQUIRED_EVIDENCE}


def _year(y, *, all_yes=True, **changed):
    row = {
        "year": y, "full_calendar_year": all_yes,
        "hco_comparability_reviewed": all_yes,
        "event_code_capture_reviewed": all_yes,
        "reviewer_accepted": all_yes,
    }
    row.update(changed)
    return row


def test_empty_input_is_blocked_and_never_authorizes_source_scan():
    r=gate.evaluate_evidence({})
    assert r["planning_state"]=="BLOCKED_NEEDS_EXTERNAL_EVIDENCE"
    assert set(r["missing_evidence_items"])==set(gate.REQUIRED_EVIDENCE)
    assert r["clinical_scan_authorized"] is False
    assert r["old_step45_execution_unblocked"] is False


def test_complete_claims_are_still_not_institutional_authorization():
    r=gate.evaluate_evidence(_full_packet())
    assert r["planning_state"]=="EVIDENCE_PACKET_READY_FOR_INDEPENDENT_AUTHORITY_REVIEW"
    assert r["clinical_scan_authorized"] is False
    assert r["data_owner_review_performed_by_this_function"] is False
    assert r["research_network_end_year"] is None
    assert r["primary_definition"].startswith("A_exact")
    assert r["sensitivity_definition"].startswith("B_provisional")


def test_hco_absence_can_be_documented_without_pretending_transfer_verified():
    entries=_full_packet()
    entries["hospital_or_episode_linkage_key_availability"]=_item(
        "documented_absent","STEWARDS_NO_PARENT_KEY","data_steward"
    )
    r=gate.evaluate_evidence(entries)
    assert r["planning_state"]=="EVIDENCE_PACKET_READY_FOR_INDEPENDENT_AUTHORITY_REVIEW"
    assert r["hco_episode_linkage_verified"] is False
    assert r["clinical_scan_authorized"] is False


def test_other_key_cannot_be_satisfied_with_documented_absence():
    entries=_full_packet()
    entries["institutional_data_use_scope"]=_item(
        "documented_absent", "NO_AUTHORIZATION", "data_owner"
    )
    r=gate.evaluate_evidence(entries)
    assert "institutional_data_use_scope" in r["invalid_evidence_items"]
    assert r["planning_state"]=="BLOCKED_NEEDS_EXTERNAL_EVIDENCE"


def test_any_rejected_requirement_triggers_explicit_redesign():
    entries=_full_packet()
    entries["institutional_data_use_scope"]=_item("rejected", "REFUSED", "data_owner")
    r=gate.evaluate_evidence(entries)
    assert r["planning_state"]=="REJECTED_MUST_REDESIGN"
    assert r["clinical_scan_authorized"] is False


def test_pending_is_not_silent_confirmation():
    entries=_full_packet()
    entries["procedure_code_systems_and_event_recording_semantics"]=_item(
        "pending","","coder"
    )
    r=gate.evaluate_evidence(entries)
    assert r["planning_state"]=="BLOCKED_NEEDS_EXTERNAL_EVIDENCE"
    assert "procedure_code_systems_and_event_recording_semantics" in r["pending_evidence_items"]


def test_false_confirmed_evidence_without_reference_invalid():
    entries=_full_packet()
    entries["legacy_git_history_privacy_review"]=_item(
        "confirmed_external","","privacy_office"
    )
    r=gate.evaluate_evidence(entries)
    assert "legacy_git_history_privacy_review" in r["invalid_evidence_items"]


@pytest.mark.parametrize("wrong",[
    {"not_in_allowed_keys":_item()},
    {"institutional_data_use_scope":{"status":"confirmed_external"}},
])
def test_unrecognized_or_unstructured_claim_rejected(wrong):
    with pytest.raises(ValueError):
        gate.evaluate_evidence(wrong)


@pytest.mark.parametrize("status",["approved","done",True,1])
def test_unknown_claim_state_fails_closed(status):
    with pytest.raises(ValueError,match="Unknown evidence state"):
        gate.evaluate_evidence({"institutional_data_use_scope":_item(status)})


def test_no_clinical_data_or_file_io_dependencies():
    from pathlib import Path
    text=Path(gate.__file__).read_text(encoding="utf-8")
    for prohibited in ("import zipfile","import sqlite3","read_bytes(", "open(", "patient.csv", "procedure.csv"):
        assert prohibited not in text


def test_no_2018_2019_research_network_assumption():
    assert gate.START_YEAR==2016
    assert gate.evaluate_evidence({})["research_network_end_year"] is None


def test_year_window_never_guesses_from_missing_information():
    r=gate.coverage_window_candidate([],current_year=2026)
    assert r["candidate_end_year"] is None
    assert r["clinical_end_year_approved"] is False


def test_contiguous_reviewed_calendar_years_yield_candidate_only():
    r=gate.coverage_window_candidate([_year(2016),_year(2017),_year(2018,all_yes=False)],current_year=2026)
    assert r["candidate_end_year"]==2017
    assert r["planning_state"]=="REVIEWED_CANDIDATE_WINDOW_NOT_APPROVED"
    assert r["clinical_end_year_approved"] is False


def test_gap_followed_by_a_later_accepted_year_does_not_claim_valid_window():
    r=gate.coverage_window_candidate([_year(2016),_year(2018)],current_year=2026)
    assert r["planning_state"]=="CONTRADICTORY_NONCONTIGUOUS_YEAR_EVIDENCE"
    assert r["candidate_end_year"] is None


def test_first_year_not_reviewed_yields_no_candidate():
    r=gate.coverage_window_candidate([_year(2016,all_yes=False),_year(2017,all_yes=False)],current_year=2026)
    assert r["planning_state"]=="NO_COMPLETE_START_YEAR"
    assert r["candidate_end_year"] is None


def test_incomplete_recent_year_not_included_even_if_present():
    r=gate.coverage_window_candidate([
        _year(2016),_year(2017),
        _year(2018,all_yes=True,reviewer_accepted=False)
    ],current_year=2026)
    assert r["candidate_end_year"]==2017


@pytest.mark.parametrize("bad",[
    [_year(2016),_year(2016)],
    [_year(2015)],
    [_year(2027)],
    [{**_year(2016),"full_calendar_year":"yes"}],
    [{**_year(2016),"extra":"field"}],
])
def test_invalid_or_duplicate_year_evidence_rejected(bad):
    with pytest.raises((ValueError,TypeError)):
        gate.coverage_window_candidate(bad,current_year=2026)


def test_no_explicit_end_year_approval_from_full_reviewed_years():
    r=gate.coverage_window_candidate([_year(2016),_year(2017)],current_year=2026)
    assert r["candidate_end_year"]==2017
    assert r["clinical_end_year_approved"] is False
