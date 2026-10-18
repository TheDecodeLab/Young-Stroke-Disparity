"""Synthetic-only Step43 tests. All test artifacts remain in ignored results/phase1/."""
from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

import pytest

from scripts.step43_neuroimaging_review_triage import (
    PHASE1, ROOT, STEP42_FIELDS, FULL, FIRST, REPORT, REVIEW,
    triage_rows, review_first, run, private_path,
)


@pytest.fixture
def workdir():
    PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step43_synthetic_", dir=PHASE1) as name:
        yield Path(name)


def build_input(folder):
    records = [
        ("CPT", "70551", "MR brain without contrast", "", "MRI_BRAIN", "historical_cpt14_anchor"),
        ("SNOMED", "TEST_A", "Magnetic resonance imaging of brain", "", "MRI_BRAIN", "textual_candidate"),
        ("SNOMED", "TEST_B", "MRI knee", "Cranial MRI", "MRI_BRAIN", "textual_candidate"),
        ("SNOMED", "TEST_C", "Personal history of magnetic resonance imaging of brain", "", "MRI_BRAIN", "textual_candidate"),
        ("SNOMED", "TEST_D", "MRI brain and neck", "", "AMBIGUOUS_HEAD_AND_NECK", "textual_candidate_needs_anatomy_review"),
        ("SNOMED", "TEST_E", "CTA neck", "", "CTA_NECK", "textual_candidate"),
        ("SNOMED", "TEST_E", "CTA head", "", "CTA_HEAD", "textual_candidate"),
        ("SNOMED", "TEST_F", "CT head", "", "CT_HEAD", "textual_candidate"),
        ("SNOMED", "TEST_G", "MRI brain", "CT head", "CT_HEAD", "textual_candidate"),
        ("SNOMED", "TEST_H", "MRI brain and neck", "", "MRI_BRAIN", "textual_candidate"),
    ]
    src = folder / "source.csv"
    status = folder / "source.json"
    with src.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, STEP42_FIELDS)
        writer.writeheader()
        for system, code, description, path, cat, reason in records:
            writer.writerow({
                "code_system": system,
                "code": code,
                "code_description": description,
                "path": path,
                "candidate_category_NOT_VALIDATED": cat,
                "discovery_reason": reason,
                "reviewer_include_LEAVE_BLANK": "",
                "reviewer_notes_LEAVE_BLANK": "",
            })
    meta = {
        "stage": "STEP42_REFERENCE_ONLY_NEUROIMAGING_CODE_DISCOVERY",
        "clinical_event_rows_examined": 0,
        "candidate_rows_n": len(records),
        "candidate_category_rows": dict(Counter(r[4] for r in records)),
        "discovery_reason_rows": dict(Counter(r[5] for r in records)),
    }
    status.write_text(json.dumps(meta))
    return src, status


def test_triage_creates_full_and_priority_without_exporting_private_codes(workdir):
    src, meta = build_input(workdir)
    original_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    result = run(src, meta, workdir, per_category=2)
    assert result["source_candidate_rows"] == 10
    assert result["all_candidate_rows_preserved_in_private_full_worksheet"] is True
    assert result["clinical_event_rows_examined"] == 0
    assert result["ready_for_imaging_outcome_ascertainment"] is False
    assert result["clinical_code_approval_provided"] is False
    with (workdir / FULL).open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 10
    tiers = {r["code"]: r["triage_bucket_NOT_CLINICALLY_VALIDATED"] for r in rows}
    assert tiers["70551"] == "A_historical_CPT_anchor"
    assert tiers["TEST_A"] == "B_description_specific"
    assert tiers["TEST_B"] == "D_path_only_or_weak_description"
    assert tiers["TEST_C"] == "F_possible_nonprocedure_concept"
    assert tiers["TEST_D"] == "E_mixed_head_and_neck"
    assert tiers["TEST_E"] == "G_same_code_multiple_categories"
    assert tiers["TEST_G"] == "C_description_disagrees_with_path"
    assert all(row["reviewer_include_LEAVE_BLANK"] == "" for row in rows)
    with (workdir / FIRST).open(newline="") as f:
        first = list(csv.DictReader(f))
    assert len(first) <= 2 * len(set(r["candidate_category_NOT_VALIDATED"] for r in rows))
    assert len(first) < len(rows)
    assert hashlib.sha256(src.read_bytes()).hexdigest() == original_hash
    public = (workdir / REPORT).read_text()
    assert "TEST_A" not in public and "70551" not in public
    assert "Magnetic resonance imaging" not in public
    for filename in (FULL, FIRST, REPORT, REVIEW):
        assert (workdir / filename).stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(workdir / REVIEW) as z:
        assert z.namelist() == [REPORT]
        assert json.loads(z.read(REPORT)) == result
        assert b"TEST_A" not in z.read(REPORT)


def test_empty_and_unapproved_fields_do_not_generate_positive_decision(workdir):
    src, meta = build_input(workdir)
    result = run(src, meta, workdir, 2)
    assert result["clinical_code_approval_provided"] is False
    assert result["ready_for_imaging_outcome_ascertainment"] is False


def test_preserve_existing_manual_annotations_without_explicit_overwrite(workdir):
    src, meta = build_input(workdir)
    run(src, meta, workdir, 2)
    manual = workdir / FIRST
    manual.write_text("DO_NOT_ERASE_CLINICIAN_WORK")
    with pytest.raises(FileExistsError, match="--overwrite"):
        run(src, meta, workdir, 2)
    assert manual.read_text() == "DO_NOT_ERASE_CLINICIAN_WORK"
    run(src, meta, workdir, 2, overwrite=True)
    assert manual.read_text() != "DO_NOT_ERASE_CLINICIAN_WORK"


def test_corrupt_counts_and_schema_fail_closed(workdir):
    src, meta = build_input(workdir)
    status = json.loads(meta.read_text())
    status["candidate_rows_n"] += 1
    meta.write_text(json.dumps(status))
    with pytest.raises(ValueError, match="row count mismatch"):
        run(src, meta, workdir, 2)
    assert not (workdir / FIRST).exists()


def test_corrupt_category_totals_fail_closed(workdir):
    src, meta = build_input(workdir)
    status = json.loads(meta.read_text())
    status["candidate_category_rows"]["MRI_BRAIN"] += 1
    meta.write_text(json.dumps(status))
    with pytest.raises(ValueError, match="category totals"):
        run(src, meta, workdir, 2)


def test_invalid_source_stage_fails_closed(workdir):
    src, meta = build_input(workdir)
    status = json.loads(meta.read_text())
    status["clinical_event_rows_examined"] = 1
    meta.write_text(json.dumps(status))
    with pytest.raises(ValueError, match="reference-only"):
        run(src, meta, workdir, 2)


def test_outside_cloned_repo_paths_forbidden(workdir):
    src, meta = build_input(workdir)
    with pytest.raises(ValueError, match="results/phase1"):
        run(src, meta, ROOT, 2)
    with pytest.raises(ValueError, match="results/phase1"):
        private_path(Path("/tmp/step43_must_not_generate"))


def test_invalid_review_batch_bound(workdir):
    src, meta = build_input(workdir)
    for amount in (0, 51):
        with pytest.raises(ValueError, match="1..50"):
            run(src, meta, workdir, amount)
