"""Synthetic-only Step 28 tests: full scanning is NEVER authorized by the default path."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import sqlite3
from zipfile import ZipFile

import pandas as pd
import pytest

from scripts.step28_imaging_extract import (
    DEFAULT_CODEBOOK, STUDY_COHORT, plan, check_approval,
    codebook, select_codes, execute, complete_db,
)


def fixture(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    for sub in ("diagnosis", "demographics", "imaging"):
        (private/sub).mkdir()
    z = tmp_path / "source.zip"
    diagnosis = "patient_id,code_system,code,principal_diagnosis_indicator,date\n" + (
        "a,ICD-10-CM,I63.9,P,20180101\n")
    patients = "patient_id,sex,race,ethnicity,year_of_birth\n" + (
        "a,F,Unknown,Unknown,1978\nb,F,Unknown,Unknown,1978\n")
    procedures = [
        ("a", "CPT", "70450", "20180101"),
        ("a", "CPT", "70551", "20180102"),
        ("a", "CPT", "70551", "20180102"),  # duplicate code-day
        ("b", "CPT", "70498", "20190101"),  # 2019: late neck CTA
        ("b", "CPT", "70546", "20190102"),  # newer MRA head
        ("b", "CPT", "70548", "20190102"),  # MRA neck
        ("b", "CPT", "70496", "20190120"),  # outside allowed seven-day window
        ("b", "HCPCS", "70498", "20190101"),  # NOT equivalent to CPT without review
        ("b", "CPT", "70450", "invalid-date"),
        ("z", "CPT", "70450", "20180101"),  # not an eligible index patient
    ]
    procedure_text = "patient_id,code_system,code,date\n" + "".join(
        ",".join(row)+"\n" for row in procedures)
    with ZipFile(z, "w") as archive:
        archive.writestr("diagnosis.csv", diagnosis)
        archive.writestr("patient.csv", patients)
        archive.writestr("procedure.csv", procedure_text)
        archive.writestr("manifest.csv",
                         f"file,row_count\ndiagnosis.csv,1\npatient.csv,2\nprocedure.csv,{len(procedures)}\n")

    def create_db(path, schema, table, records, min_age=False):
        with sqlite3.connect(path) as conn:
            conn.execute(f"CREATE TABLE {table} ({schema})")
            conn.execute("CREATE TABLE scan_state(key TEXT PRIMARY KEY,value TEXT)")
            conn.execute("INSERT INTO scan_state VALUES('scan_complete','1')")
            if min_age:
                conn.execute("INSERT INTO scan_state VALUES('min_age','19')")
                conn.execute("INSERT INTO scan_state VALUES('max_age','50')")
            placeholders=",".join(["?"]*len(records[0]))
            conn.executemany(f"INSERT INTO {table} VALUES ({placeholders})", records)

    create_db(private/"diagnosis/step18_diagnosis_index.sqlite",
        "patient_id TEXT PRIMARY KEY,index_date TEXT,dx_code TEXT",
        "first_principal_I63", [("a","20180101","I63.9"),("b","20190101","I63.9")])
    create_db(private/"demographics/step19_age_cohort.sqlite",
        "patient_id TEXT PRIMARY KEY,index_date TEXT,sex TEXT,age INTEGER,race TEXT,ethnicity TEXT",
        "eligible", [
            ("a","20180101","Female",40,"Unknown","Unknown"),
            ("b","20190101","Female",41,"Unknown","Unknown")], min_age=True)
    create_db(private/"imaging/step20_imaging_events.sqlite",
        "patient_id TEXT,modality TEXT,procedure_date TEXT",
        "imaging_event", [
            ("a","CT","20180101"),("a","MRI","20180102")])
    from scripts.step19_21_reconstruct import source_signature
    with ZipFile(z) as archive:
        signature=source_signature(archive)
    (private/"source_signature.json").write_text(json.dumps(signature))
    return private,z,signature


def approved_book(tmp_path):
    contents=DEFAULT_CODEBOOK.read_text(encoding="utf-8").replace(
        ",pending\n", ",approved\n")
    assert ",pending" not in contents
    dest=tmp_path/"approved_codes.csv"
    dest.write_text(contents,encoding="utf-8")
    return dest


def write_approval(tmp_path, spec):
    approval={
        "decision":"approved",
        "investigator_reviewer":"Synthetic Investigator",
        "clinical_reviewer":"Synthetic Neurologist",
        "approval_date":"2026-10-17",
        "codebook_sha256":spec["codebook_sha256"],
        "archive_members_sha256":spec["archive_members_sha256"],
        "study_population_identifier":STUDY_COHORT,
        "primary_window_days_each_side":1,
        "maximum_extraction_window_days_each_side":7,
        "recorded_code_outcome_only":True,
        "no_verified_encounter_claims":True,
        "data_use_review_complete":True,
    }
    p=tmp_path/"approved_protocol.json"
    p.write_text(json.dumps(approval),encoding="utf-8")
    return p


def test_candidate_catalog_pends_review():
    mapping, digest, rows = codebook(DEFAULT_CODEBOOK)
    assert len(mapping)==14
    assert len(digest)==64
    assert mapping[("CPT","70498")]=="CTA"
    assert mapping[("CPT","70549")]=="MRA"
    assert ("CPT","70471") not in mapping
    assert all(row["clinical_review"]=="pending" for row in rows)


def test_safe_plan_scans_no_clinical_rows(tmp_path):
    private,source,signature=fixture(tmp_path)
    info=plan(source,private,DEFAULT_CODEBOOK)
    assert info["stage"]=="STEP28_PREFLIGHT_ONLY"
    assert info["source_procedure_rows_declared"]==10
    assert info["procedure_rows_scanned"]==0
    assert info["approval_status"]=="NOT_APPROVED"
    assert info["private_indexed_age_19_50_patients"]==2
    assert not (private/"imaging_expanded").exists()


def test_execution_fails_closed_without_approval(tmp_path):
    private,source,signature=fixture(tmp_path)
    with pytest.raises(ValueError,match="requires --approval"):
        execute(source,private,DEFAULT_CODEBOOK,None,chunk_rows=100)
    assert not (private/"imaging_expanded").exists()


def test_execution_fails_closed_if_all_codes_pending(tmp_path):
    private,source,signature=fixture(tmp_path)
    proposed=plan(source,private,DEFAULT_CODEBOOK)
    approval=write_approval(tmp_path,proposed)
    with pytest.raises(ValueError,match="Clinical review pending"):
        execute(source,private,DEFAULT_CODEBOOK,approval,chunk_rows=100)


def test_mismatched_approval_fails(tmp_path):
    private,source,signature=fixture(tmp_path)
    approved=approved_book(tmp_path)
    proposed=plan(source,private,approved)
    approval=write_approval(tmp_path,proposed)
    data=json.loads(approval.read_text())
    data["codebook_sha256"]="0"*64
    approval.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="does not match"):
        execute(source,private,approved,approval,chunk_rows=100)


def test_patient_date_linkage_and_full_synthetic_extraction(tmp_path):
    private,source,signature=fixture(tmp_path)
    book=approved_book(tmp_path)
    proposed=plan(source,private,book)
    approval=write_approval(tmp_path,proposed)
    result=execute(source,private,book,approval,chunk_rows=100)
    assert result["manifest_row_count_verified"]
    assert result["source_procedure_rows_scanned"]==10
    assert result["matched_code_specific_patient_days"]==5
    assert result["retained_legacy_patient_modality_days"]==2
    assert result["eligible_diagnosis_first_patients"]==2
    assert result["encounter_validated"] is False
    assert result["ready_for_manuscript_inference"] is False
    assert result["windows_inclusive_days_each_side"]["7"]["total"]==2
    private_db=private/"imaging_expanded/step28_imaging_events.sqlite"
    complete_db(private_db)
    with sqlite3.connect(private_db) as conn:
        data=conn.execute("SELECT patient_id,modality,code_system,code FROM event").fetchall()
    assert ("b","CTA","CPT","70498") in data
    assert ("b","MRA","CPT","70548") in data
    assert not any(item[2]=="HCPCS" for item in data)
    with pytest.raises(FileExistsError,match="previous"):
        execute(source,private,book,approval,chunk_rows=100)


def test_source_signature_drift_fails(tmp_path):
    private,source,signature=fixture(tmp_path)
    (private/"source_signature.json").write_text(json.dumps({"archive_members_sha256":"changed"}))
    with pytest.raises(ValueError,match="does not match"):
        plan(source,private,DEFAULT_CODEBOOK)


def test_legacy_code_unmapped_rejected(tmp_path):
    content=DEFAULT_CODEBOOK.read_text().replace("CPT,70450,CT,", "CPT,70450,MRI,")
    broken=tmp_path/"broken.csv"
    broken.write_text(content)
    with pytest.raises(ValueError,match="missing or changed"):
        codebook(broken)


def test_unexpected_code_system_not_matched():
    mapping,_,_=codebook(DEFAULT_CODEBOOK)
    frame=pd.DataFrame([
        ("p","HCPCS","70498","20180101"),
        ("p","CPT","70498","20180101"),
        ("p","CPT","70546","20180101"),
        ("p","CPT","70450","20180220")
    ],columns=["patient_id","code_system","code","date"],dtype="string")
    rows=select_codes(frame,{"p":"20180101"},mapping)
    assert len(rows)==2
    assert {r[1] for r in rows}=={"CTA","MRA"}
