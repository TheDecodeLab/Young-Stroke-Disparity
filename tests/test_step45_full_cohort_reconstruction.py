"""Synthetic-only tests for guarded Step45 full-source pipeline.

No real TriNetX source read. Synthetic ZIPs, private DB and reports all remain
inside the cloned repository's ignored results/phase1/ directory.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts import step45_full_cohort_reconstruction as m


@pytest.fixture
def workspace(monkeypatch):
    (m.ROOT / "results" / "phase1").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step45_synthetic_",
                                     dir=m.ROOT / "results" / "phase1") as folder:
        private = Path(folder) / "full_reconstruction_private"
        private.mkdir(mode=0o700)
        monkeypatch.setattr(m,"PRIVATE",private)
        monkeypatch.setattr(m,"DB",private/"reconstruction_STAGE_PRIVATE.sqlite")
        monkeypatch.setattr(m,"CONFIG",private/"approvals_LOCAL_ONLY.json")
        monkeypatch.setattr(m,"CODEBOOK",private/"imaging_codebook_APPROVED_LOCAL_ONLY.csv")
        monkeypatch.setattr(m,"REPORT",private/"co_primary_cohort_aggregates_LOCAL_ONLY.json")
        # test-only fixture subdirectory is within results/phase1/; no patient-level output elsewhere
        def guarded(path):
            p=path.resolve()
            if (m.ROOT / "results" / "phase1").resolve() not in p.parents:
                raise ValueError("test outside results")
            return p
        monkeypatch.setattr(m,"private_path",guarded)
        yield private


def csv_blob(headers,rows):
    out=io.StringIO()
    w=csv.DictWriter(out,headers,lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return out.getvalue()


def build_source(private):
    people=[
        ("A","M","White",1980),  # both
        ("B","M","Black",1966),  # original only
        ("C","F","Asian",1964),  # original only
        ("D","F","White",1967),  # uniform boundary; original eligible
        ("E","M","Black",2000),  # 18th birthday uncertain
        ("F","M","Black",1965),  # original upper boundary uncertain
        ("G","Unspecified","",1985), # uniform only
        ("H","M","White",1970), # both, no imaging
    ]
    patients=[
        {"patient_id":pid,"sex":sex,"race":race,"ethnicity":"", "year_of_birth":str(yob)}
        for pid,sex,race,yob in people
    ]
    encounter=[];diagnosis=[];procedure=[]
    for i,(pid,sex,race,yob) in enumerate(people):
        eid="EVENT_"+pid
        start="20180601"; end="20180605"
        encounter.append({"patient_id":pid,"encounter_id":eid,"start_date":start,
                          "end_date":end,"type":"IMP"})
        diagnosis.append({"patient_id":pid,"encounter_id":eid,"code_system":"ICD-10-CM",
                          "code":"I63.9","date":"20180602",
                          "principal_diagnosis_indicator":"P"})
        if pid!="H":
            procedure.append({"patient_id":pid,"encounter_id":eid,"code_system":"CPT",
                              "code":"70551","date":"20180603"})
            if pid in ("A","B","D"):
                procedure.append({"patient_id":pid,"encounter_id":eid,
                                  "code_system":"CPT","code":"70496","date":"20180602"})
    # Competing later admission for A must NOT replace index
    encounter.append({"patient_id":"A","encounter_id":"SECOND_A","start_date":"20190103",
                      "end_date":"20190105","type":"IMP"})
    diagnosis.append({"patient_id":"A","encounter_id":"SECOND_A","date":"20190104",
                      "code_system":"ICD-10-CM","code":"I63.9",
                      "principal_diagnosis_indicator":"P"})
    procedure.append({"patient_id":"A","encounter_id":"SECOND_A","date":"20190104",
                      "code_system":"CPT","code":"70496"})
    # Non-principal stroke and wrong patient/image event do not enter index
    diagnosis.append({"patient_id":"A","encounter_id":"ED_A","date":"20180602",
                      "code_system":"ICD-10-CM","code":"I63.9",
                      "principal_diagnosis_indicator":"S"})
    encounter.append({"patient_id":"A","encounter_id":"ED_A","start_date":"20180602",
                      "end_date":"20180602","type":"EMER"})
    procedure.append({"patient_id":"OTHER","encounter_id":"EVENT_H","date":"20180603",
                      "code_system":"CPT","code":"70551"})
    # Shuffled relative order across tables to avoid artificial prefix joins
    encounter.reverse()
    diagnosis=diagnosis[::2]+diagnosis[1::2]
    procedure.reverse()
    headers={
        "patient.csv":["patient_id","sex","race","ethnicity","year_of_birth"],
        "encounter.csv":["patient_id","encounter_id","start_date","end_date","type"],
        "diagnosis.csv":["patient_id","encounter_id","code_system","code","date","principal_diagnosis_indicator"],
        "procedure.csv":["patient_id","encounter_id","code_system","code","date"],
    }
    data={"patient.csv":patients,"encounter.csv":encounter,
          "diagnosis.csv":diagnosis,"procedure.csv":procedure}
    src=private/"synthetic_source.zip"
    files={}
    with zipfile.ZipFile(src,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for key in ("procedure.csv","patient.csv","diagnosis.csv","encounter.csv"):
            blob=csv_blob(headers[key],data[key])
            z.writestr("synthetic/"+key,blob)
            files[key]={"present":True,"missing_expected_fields":[],
                        "uncompressed_bytes":len(blob.encode("utf-8"))}
    step36=private/"step36.json"
    step36.write_text(json.dumps({
        "stage":"STEP36_RESEARCH_METADATA_PREFLIGHT",
        "schema_supports_attempted_encounter_linkage":True,"files":files,
    }))
    approvals=m.approval_template()
    approvals.update({k:True for k in m.APPROVAL_KEYS})
    approvals["reviewer_name"]="SYNTHETIC_TEST_ONLY"
    approvals["review_date"]="2026-10-17"
    approvals["authorization_reference"]="SYNTHETIC_TEST_ONLY"
    m.CONFIG.write_text(json.dumps(approvals))
    m.CODEBOOK.write_text(
        "code_system,code,category,record_meaning,reviewer,review_date\n"
        "CPT,70551,MRI_BRAIN,performed,SYNTHETIC_TEST_ONLY,2026-10-17\n"
        "CPT,70496,CTA_HEAD,performed,SYNTHETIC_TEST_ONLY,2026-10-17\n"
    )
    return src,step36


def run_all(src,preflight):
    for stage in m.STAGES:
        m.run_stage(src,stage,m.CONFIG,m.CODEBOOK,preflight,min_free_bytes=0)


def test_two_parallel_primary_definitions_and_imaging_independent_indexes(workspace):
    source,prior=build_source(workspace)
    run_all(source,prior)
    with sqlite3.connect(m.DB) as db:
        counts=dict(db.execute("SELECT cohort,COUNT(*) FROM index_encounter GROUP BY cohort"))
        assert counts[m.DEFINITIONS[0]]==3  # A,G,H
        assert counts[m.DEFINITIONS[1]]==5  # A,B,C,D,H
        chosen=db.execute("SELECT encounter_id FROM index_encounter WHERE patient_id='A'").fetchall()
        assert chosen==[("EVENT_A",),("EVENT_A",)]
        assert db.execute("SELECT COUNT(*) FROM observed WHERE patient_id='H'").fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM observed WHERE patient_id='A' AND category='MRI_BRAIN' AND window='within_stay'").fetchone()[0]==2
        assert db.execute("SELECT COUNT(*) FROM observed WHERE patient_id='A' AND category='CTA_HEAD' AND window='within_stay'").fetchone()[0]==2
        assert db.execute("SELECT COUNT(*) FROM stages").fetchone()[0]==6
    result=json.loads(m.REPORT.read_text())
    assert result["co_primary_age_definitions"]==list(m.DEFINITIONS)
    assert result["full_source_table_passes_completed"] is True
    assert result["overlap_people_in_both_primary_cohorts_n"]=="suppressed"
    assert result["age_boundary_quality_distinct_people_LOCAL_ONLY"][m.DEFINITIONS[0]]["boundary_uncertain"]=="suppressed"
    assert "recorded_any_CTA_head_neck_within_stay_n" in result["co_primary_aggregates_LOCAL_ONLY"][m.DEFINITIONS[0]]["overall"]["all"]
    assert "no_recorded_MRI_or_vascular_within_stay_n" in result["co_primary_aggregates_LOCAL_ONLY"][m.DEFINITIONS[1]]["overall"]["all"]
    assert result["source_rows_read_by_stage"]["diagnosis"]==10
    assert result["source_rows_read_by_stage"]["encounter"]==10
    assert result["source_rows_read_by_stage"]["patient"]==8
    assert result["source_rows_read_by_stage"]["procedure"]==12
    assert "EVENT_A" not in m.REPORT.read_text()
    assert "A" not in result["co_primary_aggregates_LOCAL_ONLY"][m.DEFINITIONS[0]]["sex"]
    assert m.DB.stat().st_mode & 0o077==0
    assert m.REPORT.stat().st_mode & 0o077==0


def test_uniform_and_original_age_boundary_policy():
    day=m.parse_day("20180601")
    assert m.age_class(day,1966,"male",m.DEFINITIONS[0])=="ineligible"
    assert m.age_class(day,1966,"male",m.DEFINITIONS[1])=="eligible"
    assert m.age_class(day,1964,"female",m.DEFINITIONS[1])=="eligible"
    assert m.age_class(day,1967,"female",m.DEFINITIONS[0])=="boundary_uncertain"
    assert m.age_class(day,2000,"male",m.DEFINITIONS[1])=="boundary_uncertain"
    assert m.age_class(day,1965,"male",m.DEFINITIONS[1])=="boundary_uncertain"
    assert m.age_class(day,1985,"unknown_or_other",m.DEFINITIONS[0])=="eligible"
    assert m.age_class(day,1985,"unknown_or_other",m.DEFINITIONS[1])=="unknown"


def test_plan_does_not_create_any_database(workspace,capsys):
    source,prior=build_source(workspace)
    m.plan(source,prior)
    assert not m.DB.exists()
    assert "no clinical table rows read" in capsys.readouterr().out.lower()


def test_partial_approval_blocks_scan_before_db_creation(workspace):
    source,prior=build_source(workspace)
    d=json.loads(m.CONFIG.read_text())
    d["institutional_data_use_approved"]=False
    m.CONFIG.write_text(json.dumps(d))
    with pytest.raises(PermissionError,match="approvals missing"):
        m.run_stage(source,"diagnosis",m.CONFIG,m.CODEBOOK,prior,0)
    assert not m.DB.exists()


def test_unapproved_imaging_codebook_blocks_scan(workspace):
    source,prior=build_source(workspace)
    m.CODEBOOK.write_text("code_system,code,category,record_meaning,reviewer,review_date\n"
                          "CPT,70551,MRI_BRAIN,ordered,TEST,2026-10-17\n")
    with pytest.raises(PermissionError,match="Unapproved or ambiguous"):
        m.run_stage(source,"diagnosis",m.CONFIG,m.CODEBOOK,prior,0)
    assert not m.DB.exists()


def test_stage_order_blocks_procedure_without_index(workspace):
    source,prior=build_source(workspace)
    with pytest.raises(RuntimeError,match="Previous stage incomplete"):
        m.run_stage(source,"procedure",m.CONFIG,m.CODEBOOK,prior,0)


def test_freeze_input_approvals_and_source_provenance_across_stages(workspace):
    source,prior=build_source(workspace)
    m.run_stage(source,"diagnosis",m.CONFIG,m.CODEBOOK,prior,0)
    approvals=json.loads(m.CONFIG.read_text())
    approvals["authorization_reference"]="CHANGED_SYNTHETIC_TEST"
    m.CONFIG.write_text(json.dumps(approvals))
    with pytest.raises(RuntimeError,match="Frozen source"):
        m.run_stage(source,"encounter",m.CONFIG,m.CODEBOOK,prior,0)


def test_completed_stage_is_skipped_without_rescanning(workspace):
    source,prior=build_source(workspace)
    m.run_stage(source,"diagnosis",m.CONFIG,m.CODEBOOK,prior,0)
    with sqlite3.connect(m.DB) as db:
        before=db.execute("SELECT COUNT(*) FROM candidate").fetchone()[0]
    assert m.run_stage(source,"diagnosis",m.CONFIG,m.CODEBOOK,prior,0) is None
    with sqlite3.connect(m.DB) as db:
        assert before==db.execute("SELECT COUNT(*) FROM candidate").fetchone()[0]


def test_missing_or_contradictory_source_signature_blocks(workspace):
    source,prior=build_source(workspace)
    obj=json.loads(prior.read_text())
    obj["files"]["encounter.csv"]["uncompressed_bytes"]+=1
    prior.write_text(json.dumps(obj))
    with pytest.raises(ValueError,match="signature mismatch"):
        m.plan(source,prior)
    assert not m.DB.exists()


def test_suppression_of_small_numerator_and_complement():
    assert m.suppress(0)==0
    assert m.suppress(3)=="suppressed"
    assert m.suppress(20,1)=="suppressed"
    assert m.suppress(20,19)=="suppressed"
    assert m.suppress(22,11)==11


def test_init_template_requires_private_path_and_no_overwrite(workspace):
    m.init_templates() if not m.CONFIG.exists() else None
    assert m.CONFIG.exists() and m.CODEBOOK.exists()
    with pytest.raises(FileExistsError):
        m.init_templates()


def test_full_run_does_not_auto_approve_manual_clinical_work(workspace):
    source,prior=build_source(workspace)
    assert m.approval_template()["institutional_data_use_approved"] is False
    assert m.approval_template()["co_primary_age_definitions"] == list(m.DEFINITIONS)



def test_bloom_prefilter_has_no_false_negatives():
    bloom=m.FixedBloom()
    values=["INTERNAL_TEST_A","INTERNAL_TEST_B","_"]+[f"synthetic_{i}" for i in range(200)]
    for value in values: bloom.add(value)
    assert all(bloom.contains(value) for value in values)


def test_missing_admission_end_never_counts_as_within_stay(workspace):
    source,prior=build_source(workspace)
    for stage in ("diagnosis","encounter","patient","index"):
        m.run_stage(source,stage,m.CONFIG,m.CODEBOOK,prior,0)
    with sqlite3.connect(m.DB) as db:
        db.execute("UPDATE index_encounter SET end_day=NULL WHERE patient_id='A'")
    m.run_stage(source,"procedure",m.CONFIG,m.CODEBOOK,prior,0)
    with sqlite3.connect(m.DB) as db:
        within=db.execute(
            "SELECT COUNT(*) FROM observed WHERE patient_id='A' AND window='within_stay'"
        ).fetchone()[0]
        sensitivity=db.execute(
            "SELECT COUNT(*) FROM observed WHERE patient_id='A' AND window='same_encounter_pm7'"
        ).fetchone()[0]
    assert within==0
    assert sensitivity==4  # 2 imaging categories x 2 parallel cohorts


def test_real_execution_flags_are_not_implicit():
    # No data access or files. Strict phrase and flag are intentionally separate.
    assert m.CONFIRM=="I_ACKNOWLEDGE_FULL_TRINETX_CLINICAL_SCAN"
    assert m.approval_template()["source_linkage_policy"]=="patient_id_plus_encounter_id"
