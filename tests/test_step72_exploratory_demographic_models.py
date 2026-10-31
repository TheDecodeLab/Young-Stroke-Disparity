"""Step72 fully fabricated local-only grouped binomial model tests."""
import math
import sqlite3
from itertools import product

import numpy as np
import pandas as pd
import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step68_joint_imaging_window_scan as s68
from scripts import step72_exploratory_demographic_models as s72


@pytest.fixture
def fabricated_db():
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
    patients=[
        ("F_A","F","White","Not Hispanic or Latino",0,0,
         {"CT_HEAD":s68.IMP}),
        ("F_B","M","Black or African American","Hispanic or Latino",1,1,
         {"MRI_BRAIN":s68.NONIMP_DAY0}),
        ("F_C","",None,"",0,1,{}),
    ]
    for p,sex,race,eth,P,held,mods in patients:
        db.execute("INSERT INTO baseline.person VALUES(?,?,?,?,?)",
                   (p,1990,sex,race,eth))
        if held:
            db.execute("INSERT INTO ambiguous VALUES(?,?)",(p,p+"AMB"))
        for cohort in s62.COHORTS:
            db.execute("INSERT INTO idx VALUES(?,?,?,?)",
                       (cohort,p,"20200107",P))
            for modality,mask in mods.items():
                db.execute("INSERT INTO capture.flags VALUES(?,?,?,?)",
                           (cohort,p,modality,mask))
    db.commit()
    yield db
    db.close()


def test_no_ids_retained_and_frozen_results_reconcile(fabricated_db):
    xs=list(s72.records(fabricated_db))
    assert len(xs)==6
    for x in xs:
        assert set(x)=={"cohort","year","age_band","sex","race","ethnicity",
                         "P","held"}|set(s72.OUTCOMES)
        assert "F_A" not in repr(x) and "F_B" not in repr(x)
    frame=s72.build(fabricated_db)
    assert len(frame)==6
    assert set(frame.age_band)=={"25TO34"}
    assert "patient" not in frame.columns
    assert int(frame.n.sum())==6
    ref={"patient_cohort_aggregates":{
        "COHORT|"+c:{"n":3,"imp":1,"new_day0_other":1}
        for c in s62.COHORTS}}
    assert s72.verify(frame,ref)
    assert frame.groupby("cohort").imp_any.sum().tolist()==[1,1]
    ref["patient_cohort_aggregates"]["COHORT|"+s62.COHORTS[0]]["imp"]=2
    with pytest.raises(ValueError,match="inpatient CPT14"):
        s72.verify(frame,ref)


def _synthetic_table():
    rows=[]
    combos=product(("2018","2024"),("UNDER25","35TO44"),
                  ("MALE","FEMALE","UNKNOWN_MISSING"),
                  ("WHITE","BLACK_AFRICAN_AMERICAN","ASIAN",
                   "OTHER_OR_UNMAPPED","UNKNOWN_MISSING"),
                  ("NOT_HISPANIC_LATINO","HISPANIC_LATINO","UNKNOWN_MISSING"),
                  (0,1),(0,1))
    for year,age,sex,race,eth,P,held in combos:
        effect=(0.26*(sex=="FEMALE") -0.15*(sex=="UNKNOWN_MISSING")
                -0.30*(race=="BLACK_AFRICAN_AMERICAN")
                -0.10*(race=="ASIAN")
                +0.12*(eth=="HISPANIC_LATINO") -0.36*P -0.24*held
                +0.06*(year=="2024")+0.03*(age=="35TO44"))
        p=1/(1+math.exp(-(-0.65+effect)))
        n=60
        ip=int(round(n*p))
        adv=max(0,ip-4)
        day=min(n,ip+11+held*2)
        advday=min(day,adv+9)
        base={
            "year":year,"age_band":age,"sex":sex,"race":race,
            "ethnicity":eth,"P":P,"held":held,"n":n,
            "imp_any":ip,"imp_advanced":adv,
            "same_day_any":day,"same_day_advanced":advday,
            "CT_HEAD_imp":max(0,ip-2),
            "MRI_BRAIN_imp":max(0,adv-3),
            "CTA_HEAD_imp":max(0,adv-5),
        }
        for cohort in s62.COHORTS:
            rows.append(dict(base,cohort=cohort))
    return pd.DataFrame(rows)


def test_multivariable_models_generate_marginal_point_estimates():
    frame=_synthetic_table()
    for scope in ("quality","demographic_only","clean_only",
                  "complete_demographics"):
        result=s72.fit_one(frame,s62.COHORTS[0],"imp_any",scope)
        assert result["converged"]
        assert result["n"]>=100
        sex=[c for c in result["contrasts"] if c[0]=="sex"]
        assert len(sex)==1
        field,ref,level,n,p0,p1,rd=sex[0]
        assert (ref,level)==("MALE","FEMALE")
        assert rd>0
        assert 0<=p0<=100 and 0<=p1<=100
        assert n>=11
    with pytest.raises(ValueError,match="Unexpected outcome"):
        s72.fit_one(frame,s62.COHORTS[0],"invalid","quality")
    with pytest.raises(ValueError,match="Unknown"):
        s72.fit_one(frame,s62.COHORTS[0],"imp_any","invalid")


def test_baseline_and_sameday_nested_and_grouped():
    x=_synthetic_table()
    assert (x.same_day_any>=x.imp_any).all()
    assert (x.imp_advanced<=x.imp_any).all()
    assert (x.same_day_advanced<=x.same_day_any).all()
    ref={"patient_cohort_aggregates":{}}
    for cohort in s62.COHORTS:
        part=x[x.cohort==cohort]
        ref["patient_cohort_aggregates"]["COHORT|"+cohort]={
            "n":int(part.n.sum()),
            "imp":int(part.imp_any.sum()),
            "new_day0_other":int((part.same_day_any-part.imp_any).sum())}
    assert s72.verify(x,ref)
    x.loc[x.cohort==s62.COHORTS[0],"CT_HEAD_imp"]=1000
    with pytest.raises(ValueError,match="outcomes outside binomial"):
        s72.verify(x,ref)
