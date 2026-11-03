"""Synthetic-only tests for Step40; never read original TriNetX clinical data."""
from __future__ import annotations

import csv
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts.step40_encounter_type_review_validation import (
    PHASE1, REPORT, REVIEW_ZIP, REQUIRED_FIELDS, WORKSHEET,
    inside_private_phase1, run,
)


@pytest.fixture
def workdir():
    PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step40_synthetic_", dir=PHASE1) as path:
        yield Path(path)


def make_review_data(directory, decisions=None):
    decisions = decisions or ("", "", "", "", "")
    source = directory / "step39_status_synthetic.json"
    source.write_text(json.dumps({
        "stage": "STEP39_PRIVATE_CLINICAL_CODEBOOK_REVIEW",
        "local_worksheet_reference_rows": 5,
        "distinct_encounter_codes_with_reference": 5,
        "nonrandom_encounter_prefix_n": 85,
        "local_worksheet_created_but_EXCLUDED_FROM_REVIEW_ZIP": True,
    }), encoding="utf-8")
    worksheet = directory / "step39_worksheet_synthetic.csv"
    with worksheet.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_FIELDS)
        writer.writeheader()
        for i, (code, decision, count) in enumerate(zip(
            ("IMP", "EMER", "AMB", "OBS", "OTH"),
            decisions, (12, 11, 14, 18, 30),
        )):
            writer.writerow({
                "encounter_type_code": code,
                "reference_description": f"Synthetic clinical description {i}",
                "reference_path": "TEST_PATH",
                "prefix_record_count_NOT_PREVALENCE": count,
                "lexical_candidate_NOT_APPROVED": "unclassified",
                "clinician_decision_LEAVE_BLANK": decision,
                "reviewer_notes_LEAVE_BLANK": "SENSITIVE_REVIEWER_NOTES",
            })
    return worksheet, source


def test_blank_worksheet_reports_pending_not_approved(workdir):
    worksheet, prior = make_review_data(workdir)
    result = run(worksheet, prior, workdir)
    assert result["codebook_rows_checked"] == 5
    assert result["all_codes_have_a_nonblank_decision"] is False
    assert result["any_code_was_classified_as_inpatient"] is False
    assert result["clinical_review_complete_for_next_discussion"] is False
    assert result["inpatient_definitions_clinically_approved"] is False
    assert result["ready_for_full_linked_stroke_cohort_extraction"] is False
    assert worksheet.exists()  # never modified or removed
    content = (workdir / REPORT).read_text()
    for secret in ("IMP", "EMER", "AMB", "SENSITIVE_REVIEWER_NOTES", "TEST_PATH"):
        assert secret not in content
    assert (workdir / REPORT).stat().st_mode & 0o077 == 0
    assert (workdir / REVIEW_ZIP).stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(workdir / REVIEW_ZIP) as z:
        assert z.namelist() == [REPORT]
        assert json.loads(z.read(REPORT)) == result


def test_completed_worksheet_still_does_not_grant_approval(workdir):
    worksheet, prior = make_review_data(
        workdir,
        decisions=("inpatient", "emergency", "outpatient", "observation", "other"),
    )
    result = run(worksheet, prior, workdir)
    assert result["all_codes_have_a_nonblank_decision"] is True
    assert result["any_code_was_classified_as_inpatient"] is True
    assert result["clinical_review_complete_for_next_discussion"] is True
    assert result["inpatient_definitions_clinically_approved"] is False
    assert result["ready_for_full_linked_stroke_cohort_extraction"] is False


def test_unknown_decision_requires_followup(workdir):
    worksheet, prior = make_review_data(
        workdir, decisions=("inpatient", "emergency", "outpatient", "unknown", "other")
    )
    result = run(worksheet, prior, workdir)
    assert result["all_codes_have_a_nonblank_decision"] is True
    assert result["any_decision_is_unknown"] is True
    assert result["clinical_review_complete_for_next_discussion"] is False


def test_invalid_label_rejected_before_writing_output(workdir):
    worksheet, prior = make_review_data(
        workdir, decisions=("inpatient", "unapproved_other", "outpatient", "observation", "other")
    )
    with pytest.raises(ValueError, match="Invalid decision"):
        run(worksheet, prior, workdir)
    assert not (workdir / REPORT).exists()
    assert not (workdir / REVIEW_ZIP).exists()


def test_mismatched_prefix_count_blocks_report(workdir):
    worksheet, prior = make_review_data(workdir)
    data = json.loads(prior.read_text())
    data["nonrandom_encounter_prefix_n"] += 1
    prior.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="prefix count"):
        run(worksheet, prior, workdir)


def test_duplicate_code_row_is_rejected(workdir):
    worksheet, prior = make_review_data(workdir)
    lines = list(csv.DictReader(worksheet.open(newline="")))
    lines[-1]["encounter_type_code"] = lines[0]["encounter_type_code"]
    lines[-1]["reference_description"] = lines[0]["reference_description"]
    with worksheet.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_FIELDS)
        writer.writeheader()
        writer.writerows(lines)
    with pytest.raises(ValueError, match="Duplicate code-definition"):
        run(worksheet, prior, workdir)


def test_malformed_schema_rejected(workdir):
    worksheet, prior = make_review_data(workdir)
    lines = worksheet.read_text().splitlines()
    lines[0] = lines[0].replace("reviewer_notes_LEAVE_BLANK", "unexpected")
    worksheet.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="header"):
        run(worksheet, prior, workdir)


def test_outside_clone_paths_rejected(workdir):
    worksheet, prior = make_review_data(workdir)
    with pytest.raises(ValueError, match="results/phase1"):
        run(worksheet, prior, PHASE1.parents[1])
    with pytest.raises(ValueError, match="results/phase1"):
        inside_private_phase1(Path("/tmp/step40_public.csv"))


def test_wrong_prior_stage_rejected(workdir):
    worksheet, prior = make_review_data(workdir)
    old = json.loads(prior.read_text())
    old["stage"] = "WRONG"
    prior.write_text(json.dumps(old))
    with pytest.raises(ValueError, match="source Step39 stage"):
        run(worksheet, prior, workdir)
