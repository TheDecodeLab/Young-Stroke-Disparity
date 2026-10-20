"""Only fully fabricated patient/encounter records; no clinical fixtures."""
import csv
import io
import json
import sqlite3
import stat
import zipfile
from pathlib import Path

import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step63_ed_encounter_feasibility as s63
from scripts import step68_joint_imaging_window_scan as s68


@pytest.fixture
def fake(tmp_path,monkeypatch):
    monkeypatch.setattr(s62,"ROOT",tmp_path)
    root=tmp_path/"results/phase1/full_reconstruction_private"
    old=root/"s62_fake"
    mid=root/"s63_fake"
    new=root/"s68_fake"
    z=tmp_path/"FAKE_DO_NOT_USE.zip"
    pre=tmp_path/"step36_fake.json"
    enc=[
        ["A","AI","20200105","20200106","IMP","F","F","F"],
        ["A","AE","20200104","20200104","EMER","F","F","F"],
        ["B","BI","20200109","20200111","IMP","F","F","F"],
        ["B","BE","20200108","20200108","EMER","F","T","T"],
        ["B","BX","20200108","20200108","OTHER","F","F","F"],
        ["C","CI","20200107","20200109","IMP","F","F","F"],
        ["C","CX","20200102","20200107","OTHER","F","F","F"],
        ["D","DI","20200112","20200114","IMP","F","F","F"],
        ["D","DX","20200112","20200112","OTHER","F","F","F"],
    ]
    diag=[
        ["A","AI","ICD-10-CM","I63.9","20200105","P"],
        ["B","BI","ICD-10-CM","I63.9","20200109","S"],
        ["C","CI","ICD-10-CM","I63.9","20200107","P"],
        ["D","DI","ICD-10-CM","I63.9","20200112","P"],
    ]
    patients=[[p,"1990","F","X","Y"] for p in "ABCD"]
    proc=[
        ["A","AI","20200105","CPT","70450"],
        ["A","AE","20200104","CPT","70551"],
        ["B","BE","20200108","CPT","70551"],
        ["B","BX","20200108","CPT","70496"],
        ["C","CX","20200107","CPT","70551"],
        ["C","CX","20200102","CPT","70498"],
        ["D","DI","20200112","CPT","70498"],
        ["D","DX","20200112","CPT","70450"],
        ["B","BI","20200109","ICD-10-PCS","B030ZZZ"],
        ["D","DI","20200112","SNOMED","FAKE_CONCEPT"],
        ["OTHER","OTHER","20200112","CPT","70450"],
    ]
    source={
      "encounter":(["patient_id","encounter_id","start_date","end_date","type",
                    "start_date_derived_by_TriNetX",
                    "end_date_derived_by_TriNetX","derived_by_TriNetX"],enc),
      "diagnosis":(["patient_id","encounter_id","code_system","code","date",
                    "principal_diagnosis_indicator"],diag),
      "patient":(["patient_id","year_of_birth","sex","race","ethnicity"],patients),
      "procedure":(["patient_id","encounter_id","date","code_system","code"],proc),
    }
    info,manifest={},{}
    with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zipf:
        for name,(head,rows) in source.items():
            obj=io.StringIO(newline="")
            w=csv.writer(obj)
            w.writerow(head)
            w.writerows(rows)
            body=obj.getvalue().encode()
            zipf.writestr("fake/"+name+".csv",body)
            info[name+".csv"]={"present":True,"headers":head,
                               "uncompressed_bytes":len(body)}
            manifest[name+".csv"]={"row_count":len(rows)}
    pre.write_text(json.dumps({"stage":"STEP36_RESEARCH_METADATA_PREFLIGHT",
                "clinical_rows_read":0,"full_clinical_tables_scanned":False,
                "files":info,"relevant_manifest_counts":manifest}))
    for stage in s62.STAGES:
        assert s62.run(z,stage,preflight=pre,folder=old,chunk=3)["complete"]
    assert s63.run(z,"encounter",preflight=pre,step62_folder=old,
                   folder=mid,chunk=3)["complete"]
    assert s63.run(z,"link",preflight=pre,step62_folder=old,
                   folder=mid)["complete"]
    return z,pre,old,mid,new,len(proc)


def kw(fake):
    z,pre,old,mid,new,_=fake
    return {"zip_path":z,"folder":new,"preflight":pre,
            "step62":old/s62.DB.name,"step63":mid/s63.DATABASE,
            "chunk":2}


def test_single_scan_tests_multiple_windows_and_P(fake):
    opts=kw(fake)
    assert s68.run(**opts,stage="all")== (fake[-1],1)
    report=json.loads((fake[4]/s68.REPORT).read_text())
    with sqlite3.connect(str(fake[4]/s68.DB)) as db, sqlite3.connect(
            str(fake[2]/s62.DB.name)) as original:
        count=s68._analyze(db,original)
        cohort=count[("COHORT","uniform_18_50")]
        assert cohort["n"]==4
        assert cohort["imp"]==2
        assert cohort["new_ed"]==1
        assert cohort["new_ed_f"]==0
        assert cohort["new_pre2"]==1
        assert cohort["new_day0_other"]==1
        assert cohort["new_pre7"]==2
        assert cohort["new_any_day0"]==1
        p0=count[("P","uniform_18_50|P=0")]
        assert p0["n"]==1 and p0["imp"]==0 and p0["new_ed"]==1
        assert db.execute("""SELECT n FROM code_profile
          WHERE system='ICD-10-PCS' AND code='B030ZZZ'
            AND scope='INDEX_IMP'""").fetchone() == (2,)
        assert db.execute("""SELECT n FROM code_profile
          WHERE system='SNOMED' AND code='FAKE_CONCEPT'
            AND scope='INDEX_IMP'""").fetchone() == (2,)
        assert db.execute("""SELECT COUNT(*) FROM flags
           WHERE modality='MRI_BRAIN'""").fetchone()[0] > 0
    assert report["performed_imaging_verified"] is False
    assert report["ED_not_same_HCO_verified"] is True
    assert stat.S_IMODE((fake[4]/s68.DB).stat().st_mode)==0o600
    assert stat.S_IMODE((fake[4]/s68.REPORT).stat().st_mode)==0o600


def test_checkpoint_restart_no_double_count(fake):
    opts=kw(fake)
    assert s68.run(**opts,stage="scan",stop_after=2)==(2,0)
    assert s68.run(**opts,stage="all")== (fake[-1],1)
    with sqlite3.connect(str(fake[4]/s68.DB)) as db:
        # Each patient's two overlapping cohorts count as two, not
        # repeated because of the checkpoint restart.
        assert db.execute("""SELECT n FROM code_profile
            WHERE system='ICD-10-PCS' AND code='B030ZZZ'
              AND scope='INDEX_IMP'""").fetchone()==(2,)
    # Idempotent summary without re-reading source, including a prior report.
    assert s68.run(**opts,stage="report")== (fake[-1],1)


def test_cannot_report_before_scan_complete(fake):
    opts=kw(fake)
    with pytest.raises(ValueError,match="not been started"):
        s68.run(**opts,stage="report")
    assert s68.run(**opts,stage="scan",stop_after=2)==(2,0)
    with pytest.raises(ValueError,match="not yet complete"):
        s68.run(**opts,stage="report")


def test_primary_baseline_gate_refuses_mismatch(fake):
    opts=kw(fake)
    assert s68.run(**opts,stage="all")== (fake[-1],1)
    with sqlite3.connect(str(fake[4]/s68.DB)) as db:
        db.execute("DELETE FROM flags WHERE patient='A' AND modality='CT_HEAD'")
    with pytest.raises(ValueError,match="baseline CPT14 differs"):
        s68.run(**opts,stage="report")


def test_date_windows_do_not_imply_same_encounter():
    ep={"imp":"IP","ed":"ED","ed_start":"20200104","ed_end":"20200104",
        "ed_f":True,"start":"20200105","end":"20200106",
        "date":s68._iso("20200105")}
    ed=s68._flags(ep,"ED","20200104")
    assert ed & s68.ED and ed & s68.ED_F
    assert ed & s68.ANY_PRE2 and ed & s68.NONIMP_PRE2
    other=s68._flags(ep,"OTHER","20200105")
    assert other & s68.NONIMP_DAY0
    assert not (other & s68.IMP)
    assert not (other & s68.ED)
    assert s68._flags(ep,"OTHER","20191225")==0
