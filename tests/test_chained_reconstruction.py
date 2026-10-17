"""Synthetic end-to-end tests for the fully chained direct-ZIP pipeline."""
from pathlib import Path
import sqlite3
from zipfile import ZipFile

import pandas as pd
import pytest

from scripts.step19_21_reconstruct import (
    CPT, choose_eligible_demographics, select_imaging_events,
    run_full, source_signature,
)


DX = [
    ("a", "ICD-10-CM", "I63.9", "P", "20180101"),
    ("b", "ICD-10-CM", "I63.9", "P", "20180701"),
    ("c", "ICD-10-CM", "I63.9", "P", "20190101"),
    ("d", "ICD-10-CM", "I63.9", "P", "20181231"),
    ("e", "ICD-10-CM", "I63.9", "P", "20180401"),
    ("f", "ICD-10-CM", "I63.9", "S", "20180401"),
    ("g", "ICD-10-CM", "I63.9", "P", "20181201"),
    ("h", "ICD-10-CM", "I63.9", "P", "20180601"),
]
PATIENTS = [
    ("a", "F", "Unknown", "Unknown", "1978"),
    ("b", "M", "Unknown", "Unknown", "1978"),
    ("c", "F", "Unknown", "Unknown", "1980"),
    ("d", "M", "Unknown", "Unknown", "1977"),
    ("e", "F", "Unknown", "Unknown", "1970"),
    ("f", "F", "Unknown", "Unknown", "1980"),
    ("g", "M", "Unknown", "Unknown", "2000"),  # age 18: excluded
    ("h", "F", "Unknown", "Unknown", "1935"),  # age 83: excluded
]
PROCEDURES = [
    ("a", "CPT", "70450", "20180101"),
    ("a", "CPT", "70450", "20180101"),  # same modality/date: dedup
    ("a", "CPT", "70551", "20180105"),
    ("b", "CPT", "70450", "20180701"),  # CT-only
    ("c", "CPT", "70496", "20190102"),  # CTA but no CT
    ("e", "CPT", "70450", "20190101"),  # outside index window
    ("f", "CPT", "70450", "20180401"),  # not principal dx
    ("g", "CPT", "70450", "20181201"),  # underage
    ("h", "CPT", "70450", "20180601"),  # overage
]


def make_zip(path: Path, altered_manifest: bool = False):
    files = {
        "diagnosis.csv": ("patient_id,code_system,code,principal_diagnosis_indicator,date", DX),
        "patient.csv": ("patient_id,sex,race,ethnicity,year_of_birth", PATIENTS),
        "procedure.csv": ("patient_id,code_system,code,date", PROCEDURES),
    }
    with ZipFile(path, "w") as zf:
        for name, (header, rows) in files.items():
            zf.writestr(name, header + "\n" +
                        "".join(",".join(values) + "\n" for values in rows))
        zf.writestr("manifest.csv", "file,row_count\n" +
                    "".join(f"{name},{len(rows) + (5 if altered_manifest else 0)}\n"
                            for name, (header, rows) in files.items()))


def test_entire_pipeline_preserves_ct_only(tmp_path):
    z = tmp_path / "raw.zip"
    make_zip(z)
    private = tmp_path / "private"
    result = run_full(z, private, chunk_rows=100)
    assert result["completed_all_source_scans"] is True
    assert result["validated_admission_cohort"] is False
    assert result["ready_for_manuscript_models"] is False
    assert result["stages"][1]["eligible_n"] == 5
    summary = result["stages"][2]["aggregate_cohort_integrity"]
    assert summary == {
        "age_eligible_first_diagnosis_n": 5,
        "ct_n": 2, "mri_n": 1, "cta_n": 1, "mra_n": 0,
        "ct_only_n": 1, "ct_and_additional_n": 1,
        "advanced_no_ct_n": 1, "none_of_four_imaging_n": 2,
    }
    assert result["stages"][2]["distinct_modality_days_matched"] == 4
    assert "20180105" not in str(result)
    assert "patient_id" not in str(result)
    assert "postal_code" not in str(result)
    for database in (private / "diagnosis" / "step18_diagnosis_index.sqlite",
                     private / "demographics" / "step19_age_cohort.sqlite",
                     private / "imaging" / "step20_imaging_events.sqlite"):
        assert database.exists()
        with sqlite3.connect(database) as db:
            assert db.execute(
                "SELECT value FROM scan_state WHERE key='scan_complete'"
            ).fetchone()[0] == "1"


def test_rerun_reuses_completed_stages(tmp_path):
    z = tmp_path / "raw.zip"
    make_zip(z)
    private = tmp_path / "private"
    run_full(z, private, chunk_rows=100)
    outcome = run_full(z, private, chunk_rows=100)
    assert all(stage["reused_complete"] for stage in outcome["stages"])
    assert outcome["stages"][2]["aggregate_cohort_integrity"]["ct_only_n"] == 1


def test_sampled_sex_and_age_rules():
    frame = pd.DataFrame({
        "patient_id": ["a", "b", "c"], "sex": ["F", "M", "Unknown"],
        "race": ["White", "Black", "Unknown"],
        "ethnicity": ["Unknown"] * 3,
        "year_of_birth": ["1978", "2000", "1978"],
    }, dtype="string")
    rows, metrics = choose_eligible_demographics(
        frame, {"a": "20180101", "b": "20180101", "c": "20180101"}, 19, 50)
    assert len(rows) == 1
    assert rows[0][:4] == ("a", "20180101", "Female", 40)
    assert metrics["unrecognized_sex_rows"] == 1


def test_select_procedures_out_of_window_and_non_CPT():
    frame = pd.DataFrame([
        ("a", "CPT", "70450", "20180105"),
        ("a", "CPT", "70551", "20180201"),
        ("a", "HCPCS", "70551", "20180101"),
        ("b", "CPT", "70496", "20190101"),
    ], columns=["patient_id", "code_system", "code", "date"], dtype="string")
    rows, metrics = select_imaging_events(
        frame, {"a": "20180101", "b": "20190101"})
    assert rows == [("a", "CT", "20180105"), ("b", "CTA", "20190101")]
    assert metrics["candidate_events"] == 3
    assert metrics["within_window_events"] == 2


def test_manifest_mismatch_fails_closed(tmp_path):
    z = tmp_path / "raw.zip"
    make_zip(z, altered_manifest=True)
    with pytest.raises(ValueError, match="manifest"):
        run_full(z, tmp_path / "private", chunk_rows=100)
    assert not (tmp_path / "private" / "diagnosis" /
                "step18_diagnosis_index.sqlite").exists()


def test_source_signature_mismatch(tmp_path):
    z = tmp_path / "raw.zip"
    make_zip(z)
    private = tmp_path / "private"
    run_full(z, private, chunk_rows=100)
    with ZipFile(z, "a") as changed:
        changed.writestr("patient.csv", "patient_id,sex\nredacted,M\n")
    with pytest.raises(ValueError, match="changed"):
        run_full(z, private, chunk_rows=100)


def test_invalid_age_range(tmp_path):
    z = tmp_path / "raw.zip"
    make_zip(z)
    with pytest.raises(ValueError, match="Invalid age"):
        run_full(z, tmp_path / "private", min_age=51, max_age=50, chunk_rows=100)


def test_original_cpt_scope_is_explicit():
    assert len(CPT) == 9
    assert "70498" not in CPT  # CTA neck requires separately reviewed codebook
    assert "70546" not in CPT  # MRA head with/without contrast absent historically


def test_reused_age_cohort_requires_same_age_bounds(tmp_path):
    z = tmp_path / "raw.zip"
    make_zip(z)
    private = tmp_path / "private"
    run_full(z, private, min_age=19, max_age=50, chunk_rows=100)
    with pytest.raises(ValueError, match="different age interval"):
        run_full(z, private, min_age=19, max_age=55, chunk_rows=100)


def test_interrupted_imaging_stage_not_silently_reused(tmp_path):
    z = tmp_path / "raw.zip"
    make_zip(z)
    private = tmp_path / "private"
    run_full(z, private, chunk_rows=100)
    completed = private / "imaging" / "step20_imaging_events.sqlite"
    partial = private / "imaging" / "step20_imaging_events.partial.sqlite"
    completed.replace(partial)
    with pytest.raises(FileExistsError, match="Incomplete imaging"):
        run_full(z, private, chunk_rows=100)
