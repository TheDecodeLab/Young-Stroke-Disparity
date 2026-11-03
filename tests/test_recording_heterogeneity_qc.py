"""Synthetic tests for read-only post-expansion recording diagnostics."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from scripts.step28_imaging_extract import LITERATURE_CODEBOOK, codebook
from scripts.step32_recording_heterogeneity_qc import (
    build_flags, summarize, run, require
)


def catalog():
    return codebook(LITERATURE_CODEBOOK)[2]


def test_flags_respect_code_system_and_window():
    cohort = [("p1", "20180110", "Female", 39),
              ("p2", "20190203", "Male", 50)]
    events = [
        ("p1", "CT", "CPT", "70450", "20180110", 0),
        ("p1", "CTA", "CPT", "70498", "20180111", 1),
        ("p2", "MRA", "CPT", "70546", "20190210", 7),
    ]
    ids, flags = build_flags(cohort, events, catalog())
    assert flags["p1"][0] == 1
    assert flags["p1"][1] == flags["p1"][7]
    assert flags["p2"][3] == 0
    assert flags["p2"][7] != 0
    assert set(ids) == {"p1", "p2"}


def test_wrong_modality_and_index_date_rejected():
    cohort = [("p", "20180110", "Female", 40)]
    bad = [("p", "MRI", "CPT", "70450", "20180110", 0)]
    with pytest.raises(ValueError, match="modality mapping"):
        build_flags(cohort, bad, catalog())
    wrong_offset = [("p", "CT", "CPT", "70450", "20180110", 1)]
    with pytest.raises(ValueError, match="offset/date"):
        build_flags(cohort, wrong_offset, catalog())


def test_unknown_patient_or_duplicate_event_rejected():
    cohort = [("p", "20180110", "Male", 40)]
    foreign = [("foreign", "CT", "CPT", "70450", "20180110", 0)]
    with pytest.raises(ValueError, match="outside eligible"):
        build_flags(cohort, foreign, catalog())
    event = ("p", "CT", "CPT", "70450", "20180110", 0)
    with pytest.raises(ValueError, match="duplicate code"):
        build_flags(cohort, [event, event], catalog())


def test_all_broad_groups_can_be_reported_if_unremarkable():
    cohort, events = [], []
    for year in ("2018", "2019"):
        for sex in ("Female", "Male"):
            for age in (25, 35, 45):
                for i in range(20):
                    pid = f"{year}-{sex}-{age}-{i}"
                    day = year + "0701"
                    cohort.append((pid, day, sex, age))
                    events.append((pid, "CT", "CPT", "70450", day, 0))
    ids, flags = build_flags(cohort, events, catalog())
    groups = summarize(ids, flags)
    assert all(not g["suppressed"] for g in groups.values())
    assert sum(x["denominator"] for x in groups["age_band"]["strata"]) == 240
    assert groups["recorded_sex"]["strata"][0]["windows"]["1"]["head_CT_n"] == 120


def test_nested_small_increments_suppress_whole_dimension():
    cohort, events = [], []
    for i in range(60):
        pid = f"p{i}"
        cohort.append((pid, "20180101", "Female", 42))
        events.append((pid, "CT", "CPT", "70450", "20180101", 0))
    events.append(("p1", "CTA", "CPT", "70498", "20180101", 0))
    ids, flags = build_flags(cohort, events, catalog())
    groups = summarize(ids, flags)
    assert all(g["suppressed"] for g in groups.values())
    assert all("strata" not in g for g in groups.values())


def test_read_only_full_synthetic_private_sqlite_qc(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    for part in ("demographics", "imaging_expanded"):
        (private / part).mkdir()
    cohort_db = private / "demographics/step19_age_cohort.sqlite"
    imaging_db = private / "imaging_expanded/step28_imaging_events.sqlite"
    source_hash = "3" * 64
    catalog_digest = codebook(LITERATURE_CODEBOOK)[1]
    (private / "source_signature.json").write_text(
        json.dumps({"archive_members_sha256": source_hash}), encoding="utf-8")
    with sqlite3.connect(cohort_db) as conn:
        conn.execute("CREATE TABLE scan_state(key TEXT,value TEXT)")
        conn.executemany("INSERT INTO scan_state VALUES (?,?)",
                         [("scan_complete", "1"), ("min_age", "19"), ("max_age", "50")])
        conn.execute("CREATE TABLE eligible(patient_id TEXT,index_date TEXT,"
                     "sex TEXT,age INTEGER)")
        conn.executemany("INSERT INTO eligible VALUES (?,?,?,?)", [
            ("p1", "20180101", "Female", 25),
            ("p2", "20190101", "Male", 42),
        ])
    with sqlite3.connect(imaging_db) as conn:
        conn.execute("CREATE TABLE scan_state(key TEXT,value TEXT)")
        conn.executemany("INSERT INTO scan_state VALUES (?,?)", [
            ("scan_complete", "1"), ("codebook_sha256", catalog_digest),
            ("archive_members_sha256", source_hash),
            ("source_rows_scanned", "5"),
        ])
        conn.execute("CREATE TABLE event(patient_id TEXT,modality TEXT,"
                     "code_system TEXT,code TEXT,procedure_date TEXT,"
                     "offset_days INTEGER)")
        conn.executemany("INSERT INTO event VALUES (?,?,?,?,?,?)", [
            ("p1", "CT", "CPT", "70450", "20180101", 0),
            ("p2", "CTA", "CPT", "70496", "20190101", 0),
        ])
    report = {
        "stage": "STEP28_EXPANDED_CODE_EXTRACTION_TEMPORAL_PROXY",
        "review_basis": "published_evidence_only_no_independent_clinician_signoff",
        "encounter_validated": False,
        "approved_codebook_sha256": catalog_digest,
        "source_procedure_rows_scanned": 5,
        "matched_code_specific_patient_days": 2,
        "eligible_diagnosis_first_patients": 2,
        "anatomic_profiles_by_window": {},
    }
    for w in ("0", "1", "3", "7"):
        report["anatomic_profiles_by_window"][w] = {
            "suppressed": False,
            "head_only_primary": {"None of four": 0, "CT": 1,
                                  "MRI": 0, "CTA": 1, "MRA": 0},
            "head_plus_neck_sensitivity": {
                "None of four": 0, "CT": 1, "MRI": 0, "CTA": 1, "MRA": 0},
        }
    report_path = tmp_path / "expanded.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    result = run(private, report_path)
    assert result["denominator"] == 2
    assert result["code_specific_event_rows_read"] == 2
    assert result["original_zip_rows_scanned"] == 0
    assert result["private_patient_level_rows_exported"] == 0
    assert all(v["suppressed"] for v in
               result["groupwise_coding_diagnostics"].values())
    assert "p1" not in json.dumps(result)
    assert result["clinical_inference_allowed"] is False


def test_run_fails_if_not_owner_only(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o755)
    report = tmp_path / "report.json"
    with pytest.raises(ValueError, match="owner-only"):
        run(private, report)
