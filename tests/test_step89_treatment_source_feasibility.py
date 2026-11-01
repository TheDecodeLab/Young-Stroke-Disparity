"""Fabricated metadata and code-profile tests, no real source records."""
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("step89",ROOT/"scripts/step89_treatment_source_feasibility.py")
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


def fabricated(tmp_path):
    zpath=tmp_path/"fabricated.zip"
    headers={
        "procedure.csv":"patient_id,encounter_id,date,code_system,code\n",
        "encounter.csv":"patient_id,encounter_id,start_date,end_date,type\n",
        "patient.csv":"patient_id,sex,race,ethnicity,year_of_birth\n",
        "diagnosis.csv":"patient_id,encounter_id,date,code_system,code\n",
        "medication_drug.csv":"patient_id,encounter_id,ordered_date,drug_code\n",
        "medication_ingredient.csv":"patient_id,encounter_id,drug_ingredient\n",
    }
    with zipfile.ZipFile(zpath,"w") as z:
        for name,head in headers.items():
            z.writestr(name,head)
    inv={"stage":"STEP36_RESEARCH_METADATA_PREFLIGHT","files":{
        name:{"present":True,"headers":head.strip().split(","),
              "uncompressed_bytes":len(head.encode())}
        for name,head in headers.items() if name in ("procedure.csv","encounter.csv","patient.csv","diagnosis.csv")}}
    return zpath,inv


def test_headers_only_and_source_validation(tmp_path):
    z,inv=fabricated(tmp_path)
    data=mod.metadata(z,inv)
    assert data["medication_drug.csv"]["available"]
    assert data["medication_drug.csv"]["has_temporal_field"]
    assert not data["medication_ingredient.csv"]["has_temporal_field"]
    assert data["encounter.csv"]["has_encounter_id"]


def test_source_size_mismatch_fails(tmp_path):
    z,inv=fabricated(tmp_path)
    inv["files"]["procedure.csv"]["uncompressed_bytes"]+=1
    with pytest.raises(ValueError,match="size mismatch"):
        mod.metadata(z,inv)


def test_duplicate_metadata_member_fails(tmp_path):
    z,inv=fabricated(tmp_path)
    with zipfile.ZipFile(z,"a") as f:
        f.writestr("subfolder/medication_drug.csv","patient_id\n")
    with pytest.raises(ValueError,match="duplicate"):
        mod.metadata(z,inv)


def test_profiles_are_source_rows_not_patient_counts():
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE code_profile(system TEXT,code TEXT,scope TEXT,service_year TEXT,P INTEGER,n INTEGER)")
        db.executemany("INSERT INTO code_profile VALUES(?,?,?,?,?,?)",[
            ("CPT","61645","INDEX_IMP","2021",0,7),
            ("CPT","61645","NONIMP_DAY0","2021",1,3),
            ("CPT","37184","INDEX_IMP","2021",0,20),
            ("ICD-10-PCS","61645","INDEX_IMP","2021",0,99),
        ])
        result=mod.code_profile(db)
    assert result["61645"]["index_or_other_day0_rows"]==10
    assert result["37184"]["source_rows_total"]==20
    assert result["61645"]["service_years"]==["2021"]