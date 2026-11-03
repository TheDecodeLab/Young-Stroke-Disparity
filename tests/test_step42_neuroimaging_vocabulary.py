"""Synthetic-only Step42 vocabulary discovery tests; no clinical source data."""
from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts.step42_neuroimaging_vocabulary import (
    PHASE1, WORKSHEET, REPORT, REVIEW_ZIP, candidate_class,
    private_dir, run,
)


@pytest.fixture
def workspace():
    PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step42_test_", dir=PHASE1) as name:
        yield Path(name)


def write_synthetic_zip(folder, *, duplicate=False, missing_column=False):
    source = folder / "synthetic_reference.zip"
    fields = ["code_system", "code", "code_description", "path", "unit"]
    if missing_column:
        fields.remove("code_description")
    records = [
        ("CPT", "70551", "MR brain without contrast", "", ""),
        ("SNOMED", "SECRET_SNOMED_MRI", "Magnetic resonance imaging of brain", "", ""),
        ("SNOMED", "SECRET_SNOMED_MRA", "Magnetic resonance angiography of intracranial arteries", "", ""),
        ("SNOMED", "SECRET_SNOMED_CTA", "CT angiography of head", "", ""),
        ("SNOMED", "SECRET_SNOMED_CT", "Computed tomography of brain", "", ""),
        ("SNOMED", "SECRET_SNOMED_NECK", "CTA neck", "", ""),
        ("SNOMED", "SECRET_SNOMED_KNEE", "MRI of knee", "", ""),
        ("HCPCS", "SECRET_HCPCS_CTA", "Computed tomographic angiography of cervical vessels", "", ""),
        ("SNOMED", "SECRET_MIXED", "MRI head and neck", "", ""),
        ("Encounter Type", "IMP", "Inpatient", "", ""),
    ]
    raw = io.StringIO()
    writer = csv.DictWriter(raw, fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for system, code, description, path, unit in records:
        row = dict(code_system=system, code=code, code_description=description, path=path, unit=unit)
        writer.writerow(row)
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("reference/standardized_terminology.csv", raw.getvalue())
        if duplicate:
            z.writestr("other/standardized_terminology.csv", raw.getvalue())
    return source


def test_reference_only_generates_private_codebook_and_aggregate_zip(workspace):
    source = write_synthetic_zip(workspace)
    result = run(source, workspace, 100, 100)
    assert result["clinical_event_rows_examined"] == 0
    assert result["terminology_rows_examined"] == 10
    assert result["candidate_rows_n"] == 8
    assert result["candidate_category_rows"]["MRI_BRAIN"] == 2
    assert result["candidate_category_rows"]["MRA_HEAD"] == 1
    assert result["candidate_category_rows"]["CTA_HEAD"] == 1
    assert result["candidate_category_rows"]["CT_HEAD"] == 1
    assert result["candidate_category_rows"]["CTA_NECK"] == 2
    assert result["candidate_category_rows"]["AMBIGUOUS_HEAD_AND_NECK"] == 1
    assert result["ready_for_cohort_imaging_ascertainment"] is False
    with (workspace / WORKSHEET).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 8
    assert any(r["code"] == "SECRET_SNOMED_MRI" for r in rows)
    assert not any(r["code"] == "SECRET_SNOMED_KNEE" for r in rows)
    assert all(r["reviewer_include_LEAVE_BLANK"] == "" for r in rows)
    contents = (workspace / REPORT).read_text()
    assert "SECRET_SNOMED" not in contents
    assert "70551" not in contents
    assert "Magnetic resonance imaging" not in contents
    for name in (WORKSHEET, REPORT, REVIEW_ZIP):
        assert (workspace / name).stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(workspace / REVIEW_ZIP) as z:
        assert z.namelist() == [REPORT]
        assert json.loads(z.read(REPORT)) == result
        assert b"SECRET_SNOMED" not in z.read(REPORT)


def test_classification_excludes_nonbrain_and_mixed():
    assert candidate_class("SNOMED", "X", "MRI knee", "") is None
    assert candidate_class("SNOMED", "X", "MRA intracranial vessels", "")[0] == "MRA_HEAD"
    assert candidate_class("SNOMED", "X", "CTA brain and neck", "")[0] == "AMBIGUOUS_HEAD_AND_NECK"
    assert candidate_class("CPT", "70498", "Nonstandard text", "")[0] == "CTA_NECK"
    assert candidate_class("SNOMED", "X", "CT brain", "")[0] == "CT_HEAD"


def test_unexpected_schema_rejected(workspace):
    source = write_synthetic_zip(workspace, missing_column=True)
    with pytest.raises(ValueError, match="missing required"):
        run(source, workspace, 100, 100)
    assert not (workspace / WORKSHEET).exists()


def test_duplicate_basename_rejected(workspace):
    source = write_synthetic_zip(workspace, duplicate=True)
    with pytest.raises(ValueError, match="exactly one"):
        run(source, workspace, 100, 100)


def test_reference_rows_bound_fails_closed(workspace):
    source = write_synthetic_zip(workspace)
    with pytest.raises(ValueError, match="Terminology row limit exceeded"):
        run(source, workspace, 9, 100)
    assert not (workspace / REVIEW_ZIP).exists()


def test_candidate_count_bound_fails_closed(workspace):
    source = write_synthetic_zip(workspace)
    with pytest.raises(ValueError, match="Too many terminology candidates"):
        run(source, workspace, 100, 2)
    assert not (workspace / REVIEW_ZIP).exists()


def test_invalid_limits_rejected(workspace):
    source = write_synthetic_zip(workspace)
    with pytest.raises(ValueError, match="1..3000000"):
        run(source, workspace, 0, 100)
    with pytest.raises(ValueError, match="1..20000"):
        run(source, workspace, 100, 0)


def test_output_cannot_leave_clone(workspace):
    source = write_synthetic_zip(workspace)
    with pytest.raises(ValueError, match="results/phase1"):
        run(source, PHASE1.parents[1], 100, 100)
    with pytest.raises(ValueError, match="results/phase1"):
        private_dir(Path("/tmp/step42_outside"))
