"""All Step71 fixtures are fabricated. Never import clinical source tables."""
from collections import Counter
import sqlite3
import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step68_joint_imaging_window_scan as s68
from scripts import step71_demographic_capture_feasibility as s71


@pytest.fixture
def fake():
    db=sqlite3.connect(":memory:")
    db.executescript("""
      CREATE TABLE idx(cohort TEXT,patient TEXT,start TEXT,principal INTEGER,
        PRIMARY KEY(cohort,patient));
      CREATE TABLE ambiguous(patient TEXT,encounter TEXT,
        PRIMARY KEY(patient,encounter));
      ATTACH DATABASE ':memory:' AS baseline;
      CREATE TABLE baseline.person(patient TEXT PRIMARY KEY,
        yob INTEGER,sex TEXT,race TEXT,ethnicity TEXT);
      ATTACH DATABASE ':memory:' AS capture;
      CREATE TABLE capture.flags(cohort TEXT,patient TEXT,modality TEXT,
        mask INTEGER,PRIMARY KEY(cohort,patient,modality));
    """)
    sample=[
      ("A",0,"M","White","Not Hispanic or Latino",False,
       {"CT_HEAD":s68.IMP}),
      ("B",1,"FEMALE","Black or African American","Hispanic or Latino",True,
       {"MRI_BRAIN":s68.NONIMP_DAY0}),
      ("C",1,"male","unknown","",True,
       {"CT_HEAD":s68.IMP,"CTA_HEAD":s68.NONIMP_DAY0}),
      ("D",0,"","Synthetic special label","Unmapped synthetic",False,
       {}),
    ]
    for p,P,sex,race,ethnicity,held,modalities in sample:
        db.execute("INSERT INTO baseline.person VALUES(?,?,?,?,?)",
                   (p,1990,sex,race,ethnicity))
        if held:
            db.execute("INSERT INTO ambiguous VALUES(?,?)",
                       (p,p+"FAKE_ENCOUNTER"))
        for cohort in s62.COHORTS:
            db.execute("INSERT INTO idx VALUES(?,?,?,?)",
                       (cohort,p,"20200105",P))
            for modality,mask in modalities.items():
                db.execute("INSERT INTO capture.flags VALUES(?,?,?,?)",
                           (cohort,p,modality,mask))
    db.commit()
    yield db
    db.close()


def test_recorded_any_and_advanced_are_separate(fake):
    counts=s71.analyze(fake)
    for cohort in s62.COHORTS:
        x=counts[("COHORT",cohort)]
        assert x["n"]==4
        assert x["P1"]==2 and x["held"]==2
        assert x["imp_any"]==2 and x["same_day_any"]==3
        assert x["day0_new_any"]==1
        assert x["imp_advanced"]==0 and x["same_day_advanced"]==2
        assert x["day0_new_advanced"]==2
        assert x["CT_HEAD_imp"]==2
        assert x["MRI_BRAIN_imp"]==0
        ref={"patient_cohort_aggregates":{
            "COHORT|"+co:{
              "n":4,"imp":2,"new_day0_other":1,"new_ed":0}
            for co in s62.COHORTS}}
        assert s71.verify(fake,counts,ref)
        assert counts[("SEX",cohort+"|MALE")]["n"]==2
        assert counts[("SEX",cohort+"|FEMALE")]["n"]==1
        assert counts[("SEX",cohort+"|UNKNOWN_MISSING")]["n"]==1
        assert counts[("RACE",cohort+"|UNKNOWN_MISSING")]["n"]==1
        assert counts[("RACE",cohort+"|OTHER_OR_UNMAPPED")]["n"]==1


def test_category_normalization_is_conservative():
    assert s71.category("SEX","F")=="FEMALE"
    assert s71.category("SEX","mAlE")=="MALE"
    assert s71.category("ETHNICITY","")=="UNKNOWN_MISSING"
    assert s71.category("ETHNICITY","Not Hispanic or Latino")=="NOT_HISPANIC_LATINO"
    assert s71.category("RACE","Two or more races")=="MULTIRACIAL"
    assert s71.category("RACE","Unvalidated fake ethnicity")=="OTHER_OR_UNMAPPED"
    assert s71.category("RACE","Declined")=="UNKNOWN_MISSING"
    with pytest.raises(ValueError,match="Unsupported"):
        s71.category("OTHER","FAKE")


def test_partition_and_reference_mismatch_is_detected(fake):
    rows=s71.analyze(fake)
    cohort=s62.COHORTS[0]
    ref={"patient_cohort_aggregates":{
        "COHORT|"+co:{"n":4,"imp":2,
                      "new_day0_other":1,"new_ed":0}
        for co in s62.COHORTS}}
    assert s71.verify(fake,rows,ref)
    rows[("RACE",cohort+"|WHITE")]["n"]+=1
    with pytest.raises(AssertionError,match="partition"):
        s71.verify(fake,rows,ref)
    rows[("RACE",cohort+"|WHITE")]["n"]-=1
    ref["patient_cohort_aggregates"]["COHORT|"+cohort]["imp"]=3
    with pytest.raises(ValueError,match="original Step68"):
        s71.verify(fake,rows,ref)


def test_does_not_print_raw_demographics_or_private_identifiers(fake,capsys):
    counts=s71.analyze(fake)
    s71.display(counts)
    txt=capsys.readouterr().out
    assert "SUPPRESSED category n<11" in txt
    assert "Synthetic special label" not in txt
    assert "Unmapped synthetic" not in txt
    assert "FAKE_ENCOUNTER" not in txt
    assert "CPT14" in txt


def test_zero_and_only_other_day0_advanced():
    x=s71.measure({"MRI_BRAIN":s68.NONIMP_DAY0,
                   "CT_HEAD":s68.IMP},1,True)
    assert x["imp_any"]==1 and x["day0_new_any"]==0
    assert x["imp_advanced"]==0 and x["day0_new_advanced"]==1
    assert x["same_day_advanced"]==1
    with pytest.raises(ValueError,match="Unknown CPT14"):
        s71.measure({"UNKNOWN_MODALITY":s68.IMP},0,False)
