"""Synthetic-only Step44 tests: files confined to ignored results/phase1/."""
from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts.step43_neuroimaging_review_triage import FIELDS as STEP43_FIELDS
from scripts.step44_anatomy_ambiguity_review import (
    PHASE1, ROOT, FIRST, FULL, REPORT, REVIEW,
    ambiguity_origin, private_path, run,
)


@pytest.fixture
def workdir():
    PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step44_synthetic_", dir=PHASE1) as folder:
        yield Path(folder)


def create_prior(workdir):
    source = workdir / "step43_full_synthetic.csv"
    status = workdir / "step43_status_synthetic.json"
    cases = [
        ("S1", "CTA of head", "Head and neck CT angiography",
         "AMBIGUOUS_HEAD_AND_NECK", "CTA_HEAD"),
        ("S2", "Magnetic resonance angiography of intracranial arteries",
         "Head and neck MRI/MRA", "AMBIGUOUS_HEAD_AND_NECK", "MRA_HEAD"),
        ("S3", "MRI head and neck", "MR procedures",
         "AMBIGUOUS_HEAD_AND_NECK", "AMBIGUOUS_HEAD_AND_NECK"),
        ("S4", "Unclear source concept", "CTA head and neck",
         "AMBIGUOUS_HEAD_AND_NECK", "NONE"),
        ("S5", "=HYPERLINK('BAD')", "MRI head and neck",
         "AMBIGUOUS_HEAD_AND_NECK", "OTHER"),
        ("S6", "MRI brain", "Brain magnetic resonance imaging",
         "MRI_BRAIN", "MRI_BRAIN"),
    ]
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, STEP43_FIELDS)
        writer.writeheader()
        for code, description, path, original, desc_only in cases:
            writer.writerow({
                "code_system": "SNOMED",
                "code": code,
                "code_description": description,
                "path": path,
                "candidate_category_NOT_VALIDATED": original,
                "discovery_reason": "textual_candidate",
                "reviewer_include_LEAVE_BLANK": "",
                "reviewer_notes_LEAVE_BLANK": "",
                "triage_bucket_NOT_CLINICALLY_VALIDATED": (
                    "E_mixed_head_and_neck" if original == "AMBIGUOUS_HEAD_AND_NECK"
                    else "B_description_specific"
                ),
                "description_only_modality_anatomy_match": desc_only,
                "suspected_nonprocedure_concept_FOR_REVIEW": "no",
                "code_has_multiple_candidate_categories_FOR_REVIEW": "no",
            })
    status.write_text(json.dumps({
        "stage": "STEP43_REFERENCE_CODEBOOK_REVIEW_TRIAGE",
        "clinical_event_rows_examined": 0,
        "all_candidate_rows_preserved_in_private_full_worksheet": True,
        "source_candidate_rows": len(cases),
        "full_candidate_category_counts": {
            "AMBIGUOUS_HEAD_AND_NECK": 5, "MRI_BRAIN": 1,
        },
        "triage_bucket_counts": {
            "E_mixed_head_and_neck": 5, "B_description_specific": 1,
        },
    }), encoding="utf-8")
    return source, status


def test_split_ambiguity_and_no_raw_terms_exported(workdir):
    source, status = create_prior(workdir)
    initial_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    result = run(source, status, workdir, 1)
    assert result["clinical_event_rows_examined"] == 0
    assert result["source_candidates_n"] == 6
    assert result["original_ambiguous_candidates_n"] == 5
    assert result["full_ambiguous_reference_rows_preserved"] is True
    assert result["clinical_disparities_cohort_authorized"] is False
    assert result["no_automatic_code_reclassification_or_inclusion"] is True
    assert result["review_first_rows_n"] == 4
    with (workdir / FULL).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 5
    assert "S6" not in {r["code"] for r in rows}
    sub = {r["code"]: r["anatomy_ambiguity_origin_NOT_APPROVED"] for r in rows}
    assert sub["S1"] == "description_specific_but_reference_path_mixed"
    assert sub["S2"] == "description_specific_but_reference_path_mixed"
    assert sub["S3"] == "head_and_neck_mixed_in_description"
    assert sub["S4"] == "only_reference_path_indicates_anatomy"
    assert sub["S5"] == "other_description_disagreement"
    assert all(r["reviewer_include_LEAVE_BLANK"] == "" for r in rows)
    assert "'=HYPERLINK" in (workdir / FULL).read_text()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == initial_sha
    with zipfile.ZipFile(workdir / REVIEW) as z:
        assert z.namelist() == [REPORT]
        report = json.loads(z.read(REPORT))
        assert report == result
        for secret in ("S1", "S2", "HYPERLINK", "CTA of head"):
            assert secret not in z.read(REPORT).decode()
    for name in (FULL, FIRST, REPORT, REVIEW):
        assert (workdir / name).stat().st_mode & 0o077 == 0


def test_ambiguous_subtypes_are_only_review_labels():
    assert ambiguity_origin({"description_only_modality_anatomy_match": "MRA_NECK"}) == "description_specific_but_reference_path_mixed"
    assert ambiguity_origin({"description_only_modality_anatomy_match": "NONE"}) == "only_reference_path_indicates_anatomy"


def test_existing_notes_are_not_overwritten(workdir):
    source, status = create_prior(workdir)
    run(source, status, workdir)
    note = workdir / FIRST
    note.write_text("REVIEWED_DO_NOT_REMOVE")
    with pytest.raises(FileExistsError, match="--overwrite"):
        run(source, status, workdir)
    assert note.read_text() == "REVIEWED_DO_NOT_REMOVE"
    run(source, status, workdir, overwrite=True)
    assert note.read_text() != "REVIEWED_DO_NOT_REMOVE"


def test_reconcile_source_categories(workdir):
    source, status = create_prior(workdir)
    p = json.loads(status.read_text())
    p["full_candidate_category_counts"]["MRI_BRAIN"] = 2
    status.write_text(json.dumps(p))
    with pytest.raises(ValueError, match="category totals"):
        run(source, status, workdir)
    assert not (workdir / REVIEW).exists()


def test_wrong_source_stage_blocks_output(workdir):
    source, status = create_prior(workdir)
    p = json.loads(status.read_text())
    p["clinical_event_rows_examined"] = 1
    status.write_text(json.dumps(p))
    with pytest.raises(ValueError, match="complete reference-only source"):
        run(source, status, workdir)


def test_wrong_source_header_blocks_output(workdir):
    source, status = create_prior(workdir)
    lines = source.read_text().splitlines()
    lines[0] = lines[0].replace("code_description", "unexpected_name")
    source.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="header"):
        run(source, status, workdir)


def test_no_output_outside_cloned_repo(workdir):
    source, status = create_prior(workdir)
    with pytest.raises(ValueError, match="results/phase1"):
        run(source, status, ROOT, 1)
    with pytest.raises(ValueError, match="results/phase1"):
        private_path(Path("/tmp/step44_public"))


@pytest.mark.parametrize("limit", [0, 51])
def test_limits_checked(workdir, limit):
    source, status = create_prior(workdir)
    with pytest.raises(ValueError, match="1..50"):
        run(source, status, workdir, limit)
