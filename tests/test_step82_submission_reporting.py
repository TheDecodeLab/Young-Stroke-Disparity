"""Fabricated fixtures only. Never read a real TriNetX database in tests."""
from pathlib import Path
import importlib.util
import json
import os
import sqlite3
import stat

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/step82_submission_reporting.py"
SPEC = importlib.util.spec_from_file_location("step82_submission_reporting", SCRIPT)
s82 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s82)


def mock_age_class(day, yob, sex, cohort):
    assert cohort == s82.PRIMARY
    if yob is None:
        return "unknown_yob"
    low, high = int(day[:4]) - yob - 1, int(day[:4]) - yob
    if low >= 18 and high <= 50:
        return "definite"
    if high < 18 or low > 50:
        return "excluded"
    return "boundary_uncertain"


def mock_category(kind, x):
    mapping = {
        "SEX": {"M": "MALE", "F": "FEMALE", "": "UNKNOWN_MISSING"},
        "RACE": {"W": "WHITE", "B": "BLACK_AFRICAN_AMERICAN"},
        "ETHNICITY": {"N": "NOT_HISPANIC_LATINO", "H": "HISPANIC_LATINO"},
    }
    return mapping[kind].get(x or "", "OTHER_OR_UNMAPPED")


def fixture_db():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE progress(stage TEXT, seen INTEGER, done INTEGER);
        CREATE TABLE admission(patient TEXT, encounter TEXT, start TEXT, end TEXT, principal INTEGER);
        CREATE TABLE ambiguous_admission(patient TEXT, encounter TEXT);
        CREATE TABLE person(patient TEXT, yob INTEGER, sex TEXT, race TEXT, ethnicity TEXT);
        CREATE TABLE idx(cohort TEXT, patient TEXT, encounter TEXT, start TEXT, end TEXT, principal INTEGER);
        CREATE TABLE audit(cohort TEXT, finding TEXT, n INTEGER);
    """)
    db.executemany("INSERT INTO progress VALUES(?,0,1)", [(x,) for x in s82.REQUIRED_STAGES])
    db.executemany("INSERT INTO person VALUES(?,?,?,?,?)", [
        ("A", 1990, "M", "W", "N"),
        ("B", 1985, "F", "B", "H"),
        ("C", 1995, "M", "W", "N"),
        ("D", None, "F", "W", "N"),
        ("E", 2002, "M", "B", "N"),
        ("F", 1950, "F", "W", "N"),
    ])
    db.executemany("INSERT INTO admission VALUES(?,?,?,?,?)", [
        ("A", "a1", "20200115", "20200119", 0),
        ("B", "b1", "20200201", "20200202", 1),
        ("C", "c1", "20200110", "20200111", 0),
        ("C", "c2", "20200110", "20200112", 0),
        ("D", "d1", "20200301", "20200302", 0),
        ("E", "e1", "20160101", "20160102", 0),
        ("E", "e2", "20200101", "20200102", 0),
        ("F", "f1", "20200101", "20200102", 0),
    ])
    db.executemany("INSERT INTO idx VALUES(?,?,?,?,?,?)", [
        (s82.PRIMARY, "A", "a1", "20200115", "20200119", 0),
        (s82.PRIMARY, "B", "b1", "20200201", "20200202", 1),
    ])
    db.executemany("INSERT INTO audit VALUES(?,?,?)", [
        (s82.PRIMARY, "candidate_admission_age_definite", 4),
        (s82.PRIMARY, "candidate_admission_age_unknown_yob", 1),
        (s82.PRIMARY, "candidate_admission_age_boundary_uncertain", 1),
        (s82.PRIMARY, "candidate_admission_age_excluded", 2),
        (s82.PRIMARY, "patient_held_competing_same_day_index_encounters", 1),
    ])
    db.execute("INSERT INTO ambiguous_admission VALUES('F','conflict')")
    return db


def test_patient_flow_and_baseline_reconcile():
    with fixture_db() as db:
        report = s82.aggregate_report(db, mock_age_class, mock_category)
    flow = report["patient_flow_not_full_export_flow"]
    assert flow["candidate_retained_imp_keys"] == 8
    assert flow["candidate_unique_patients"] == 6
    assert flow["patient_flow"] == {
        "included_indexed": 2,
        "held_competing_same_day_definite_index": 1,
        "no_definite_missing_birth_year": 1,
        "no_definite_age_boundary_uncertain": 1,
        "no_definite_age_outside_range": 1,
    }
    assert flow["admission_age_audit_not_patient_exclusions"]["candidate_admission_age_definite"] == 4
    assert report["quarantined_conflicting_imp_keys_outside_flow"] == 1
    assert report["baseline"]["n"] == 2
    assert report["baseline"]["P0"] == report["baseline"]["P1"] == 1
    age = {r["category"]: r["n_total"] for r in report["baseline"]["category_tables"]["AGE_BAND"]}
    assert age == {"25-34": 1, "CROSSES_AGE_BAND_BOUNDARY": 1}
    labels = [r["category"] for rows in report["baseline"]["category_tables"].values() for r in rows]
    assert "W" not in labels and "B" not in labels  # no raw source labels
    assert report["baseline"]["preliminary_small_cell_or_complement_flags"]


def test_rejects_partial_checkpoint():
    with fixture_db() as db:
        db.execute("UPDATE progress SET done=0 WHERE stage='procedure'")
        with pytest.raises(ValueError, match="not all complete"):
            s82.check_frozen(db)


def test_mismatched_audit_fails_closed():
    with fixture_db() as db:
        db.execute("UPDATE audit SET n=3 WHERE finding='candidate_admission_age_definite'")
        with pytest.raises(AssertionError, match="Admission-level"):
            s82.cohort_flow(db, s82.PRIMARY, mock_age_class)


def test_missing_frozen_index_flag_fails_closed():
    with fixture_db() as db:
        db.execute("DELETE FROM idx WHERE patient='B'")
        with pytest.raises(AssertionError, match="Competing same-day"):
            s82.cohort_flow(db, s82.PRIMARY, mock_age_class)


def test_rejects_unexpected_demographic_mapping():
    with fixture_db() as db:
        def bad_cat(kind, value):
            return "RAW_SOURCE_TEXT"
        with pytest.raises(ValueError, match="Unexpected mapped category"):
            s82.baseline(db, s82.PRIMARY, bad_cat)


def test_private_report_mode_no_overwrite_no_escape(monkeypatch, tmp_path):
    private_root = tmp_path / "results/phase1/full_reconstruction_private"
    private_root.mkdir(parents=True)
    monkeypatch.setattr(s82, "PRIVATE_ROOT", private_root)
    p = s82.write_private_report({"policy": "LOCAL"}, private_root / "step82")
    assert json.loads(p.read_text()) == {"policy": "LOCAL"}
    assert stat.S_IMODE(p.stat().st_mode) == 0o600
    assert stat.S_IMODE(p.parent.stat().st_mode) == 0o700
    with pytest.raises(FileExistsError):
        s82.write_private_report({"policy": "DIFFERENT"}, p.parent)
    with pytest.raises(ValueError):
        s82.write_private_report({}, tmp_path / "outside")


def test_age_band_uses_both_possible_ages():
    assert s82.age_band("20200115", 1990) == "25-34"
    assert s82.age_band("20200201", 1985) == "CROSSES_AGE_BAND_BOUNDARY"
    assert s82.age_band("20200301", None) == "UNKNOWN_BIRTH_YEAR"


def test_cohort_flow_without_exclusions_is_allowed():
    db = fixture_db()
    try:
        db.execute("DELETE FROM admission WHERE patient NOT IN ('A','B')")
        db.execute("DELETE FROM audit")
        db.executemany("INSERT INTO audit VALUES(?,?,?)", [
            (s82.PRIMARY, "candidate_admission_age_definite", 2),
            (s82.PRIMARY, "patient_held_competing_same_day_index_encounters", 0),
        ])
        flow = s82.cohort_flow(db, s82.PRIMARY, mock_age_class)
        assert flow["candidate_unique_patients"] == flow["indexed_patients_reconcile"] == 2
    finally:
        db.close()


def test_verify_frozen_report_reconciles_and_detects_mismatch():
    with fixture_db() as db:
        report = s82.aggregate_report(db, mock_age_class, mock_category)
    prior = {
        "stage": "STEP62_PROVISIONAL_PRIVATE_RECONSTRUCTION",
        "cohorts": {s82.PRIMARY: {
            "indexed_patients_not_validated": 2,
            "by_start_year": {"2020": {"index_cases": 2, "with_P_label": 1}},
            "candidate_admission_age_QA_NOT_patient_denominators": {
                **report["patient_flow_not_full_export_flow"]["admission_age_audit_not_patient_exclusions"],
                "patient_held_competing_same_day_index_encounters": 1,
            },
        }},
        "encounter_key_integrity_LOCAL_ONLY": {
            "quarantined_qualifying_IMP_keys_with_conflicting_dates": 1,
            "remaining_matched_IMP_encounter_keys": 8,
        },
    }
    assert s82.verify_frozen_step62_report(report,prior)
    prior["cohorts"][s82.PRIMARY]["by_start_year"]["2020"]["with_P_label"] = 2
    with pytest.raises(AssertionError, match="P flag count"):
        s82.verify_frozen_step62_report(report,prior)
