"""Synthetic-only tests for Step 23-24; no clinical data."""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
from zipfile import ZipFile

import pandas as pd
import pytest

from scripts.step23_24_eligibility_qc import (
    analyze_codes, count_demographic_chunk, load_complete, run,
)


def dataframes():
    dx = pd.DataFrame([
        ("a", "20180105", "I63.9"), ("b", "20190505", "I63.4"),
        ("c", "20180105", "I63.1"), ("d", "20180105", "I63.9"),
        ("e", "20180105", "I63.9"), ("f", "20180105", "I63.9"),
    ], columns=["patient_id", "index_date", "dx_code"])
    cohort = pd.DataFrame([
        ("a", "20180105", "Female", 40, "Unknown", "Unknown"),
        ("b", "20190505", "Male", 39, "White", "Not Hispanic"),
    ], columns=["patient_id", "index_date", "sex", "age", "race", "ethnicity"])
    imaging = pd.DataFrame([
        ("a", "CT", "20180105"), ("a", "MRI", "20180107"),
        ("b", "CT", "20190505"),
    ], columns=["patient_id", "modality", "procedure_date"])
    source = pd.DataFrame([
        ("a", "F", "1978"), ("b", "M", "1980"), ("c", "F", "2005"),
        ("d", "M", "1950"), ("e", "F", ""), ("f", "Unknown", "1978"),
        ("other", "M", "1970"),
    ], columns=["patient_id", "sex", "year_of_birth"])
    return dx, cohort, imaging, source


def archive(path: Path):
    dx, cohort, imaging, source = dataframes()
    with ZipFile(path, "w") as z:
        z.writestr("patient.csv", source.to_csv(index=False))
        z.writestr("diagnosis.csv", "placeholder\n")
        z.writestr("procedure.csv", "placeholder\n")
        z.writestr("manifest.csv", "file,row_count\npatient.csv,7\n")
    from scripts.step19_21_reconstruct import source_signature
    with ZipFile(path) as z:
        return source_signature(z)


def make_fixture(tmp_path):
    dx, cohort, imaging, source = dataframes()
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    for sub in ("diagnosis", "demographics", "imaging"):
        (root / sub).mkdir()
    z = tmp_path / "test.zip"
    (root / "source_signature.json").write_text(json.dumps(archive(z)))
    definitions = [
        ("diagnosis/step18_diagnosis_index.sqlite", "first_principal_I63",
         "patient_id TEXT PRIMARY KEY,index_date TEXT,dx_code TEXT", dx),
        ("demographics/step19_age_cohort.sqlite", "eligible",
         "patient_id TEXT PRIMARY KEY,index_date TEXT,sex TEXT,age INTEGER,race TEXT,ethnicity TEXT",
         cohort),
        ("imaging/step20_imaging_events.sqlite", "imaging_event",
         "patient_id TEXT,modality TEXT,procedure_date TEXT", imaging),
    ]
    for relative, table, schema, frame in definitions:
        with sqlite3.connect(root / relative) as conn:
            conn.execute(f"CREATE TABLE {table} ({schema})")
            conn.execute("CREATE TABLE scan_state(key TEXT,value TEXT)")
            conn.execute("INSERT INTO scan_state VALUES('scan_complete','1')")
            frame.to_sql(table, conn, if_exists="append", index=False)
    return root, z


def test_exclusive_demographic_attrition():
    dx, cohort, imaging, source = dataframes()
    counts, found = count_demographic_chunk(
        source, dict(zip(dx.patient_id, dx.index_date)), set(cohort.patient_id))
    assert len(found) == 6
    assert counts["eligible_19_50"] == 2
    assert counts["age_under_19"] == 1
    assert counts["age_over_50"] == 1
    assert counts["missing_or_invalid_birth_year"] == 1
    assert counts["unrecognized_sex"] == 1


def test_code_diagnostics_suppress_all_groups_if_any_small():
    dx, cohort, imaging, source = dataframes()
    r = analyze_codes(dx, cohort, imaging)
    assert len(r["coarse_icd10_group_by_imaging"]) == 2
    assert all(g["suppressed"] for g in r["coarse_icd10_group_by_imaging"])
    assert all("eligible_total" not in g for g in r["coarse_icd10_group_by_imaging"])
    assert len(r["missing_race_ethnicity_by_imaging_group"]) == 2
    assert "patient_id" not in r


def test_unknown_procedure_patient_is_rejected():
    dx, cohort, imaging, source = dataframes()
    imaging.loc[0, "patient_id"] = "unknown"
    with pytest.raises(ValueError, match="noneligible"):
        analyze_codes(dx, cohort, imaging)


def test_complete_targeted_audit_and_no_row_level_exports(tmp_path):
    private, z = make_fixture(tmp_path)
    r = run(private, z, chunk_rows=100)
    assert r["demographic_attrition"]["saved_eligible_patients_reconciled_n"] == 2
    assert r["demographic_attrition"]["original_patient_source_rows_verified"] == 7
    assert r["diagnosis_procedure_source_records_rescanned"] == 0
    assert "20180105" not in str(r)
    assert '"patient_id":' not in json.dumps(r)
    assert r["clinical_inference_allowed"] is False


def test_incomplete_stage_rejected(tmp_path):
    private, z = make_fixture(tmp_path)
    with sqlite3.connect(private / "imaging/step20_imaging_events.sqlite") as conn:
        conn.execute("UPDATE scan_state SET value='0' WHERE key='scan_complete'")
    with pytest.raises(ValueError, match="Incomplete"):
        run(private, z, chunk_rows=100)


def test_incorrect_prior_step22_rejected(tmp_path):
    private, z = make_fixture(tmp_path)
    prior = tmp_path / "incorrect.json"
    prior.write_text(json.dumps({
        "stage": "STEP22_LOCAL_SQLITE_VALIDATION_ONLY",
        "age_eligible_n": 999,
        "matched_distinct_modality_days": 3,
        "full_diagnosis_index_patients": 6,
    }))
    with pytest.raises(ValueError, match="Step 22"):
        run(private, z, chunk_rows=100, prior_step22=prior)


def test_wrong_archive_signature_rejected(tmp_path):
    private, z = make_fixture(tmp_path)
    (private / "source_signature.json").write_text(json.dumps({"changed": True}))
    with pytest.raises(ValueError, match="ZIP differs"):
        run(private, z, chunk_rows=100)


def test_coarse_codes_reconcile_without_small_cells():
    dx, cohort, imaging, source = dataframes()
    # Generate a large synthetic cohort, preserving index/date consistency.
    dx_records = []
    cohort_records = []
    imaging_records = []
    for prefix, code in (("n", "I63.9"), ("o", "I63.4")):
        for index in range(60):
            patient = f"{prefix}{index}"
            dx_records.append((patient, "20180105", code))
            cohort_records.append((patient, "20180105", "Male", 35, "Unknown", "Unknown"))
            modality = ("CT", "MRI", "CTA", "MRA")[index % 4]
            imaging_records.append((patient, modality, "20180105"))
    dx = pd.DataFrame(dx_records, columns=["patient_id", "index_date", "dx_code"])
    cohort = pd.DataFrame(cohort_records, columns=[
        "patient_id", "index_date", "sex", "age", "race", "ethnicity"])
    imaging = pd.DataFrame(imaging_records, columns=[
        "patient_id", "modality", "procedure_date"])
    result = analyze_codes(dx, cohort, imaging)
    coarse = result["coarse_icd10_group_by_imaging"]
    assert len(coarse) == 2
    assert all(not entry["suppressed"] for entry in coarse)
    assert sum(entry["eligible_total"] for entry in coarse) == 120
    assert sum(entry["imaging_groups"]["CT only"] for entry in coarse) == 30
    assert "first_decimal_digit_audit_by_imaging" not in result
