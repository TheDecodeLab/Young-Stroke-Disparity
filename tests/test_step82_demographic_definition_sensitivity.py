"""Fabricated-only checks for Step82 grouped-patient sensitivity and safeguards."""
from collections import Counter
import math

import pandas as pd
import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step68_joint_imaging_window_scan as s68
from scripts import step82_demographic_definition_sensitivity as s82


def patient(sex, race, ethnicity, P, held, ct_imp, ct_day, mri_imp=0):
    mods={}
    if ct_day:
        mods["CT_HEAD"]=(s68.IMP if ct_imp else 0)|(
            s68.NONIMP_DAY0 if ct_day and not ct_imp else 0)
    if mri_imp:
        mods["MRI_BRAIN"]=s68.IMP
    assert s82.PRIMARY==s62.COHORTS[0]
    return s82.classify_record(
        (s82.PRIMARY,"2020",P,1990,sex,race,ethnicity,held),mods)


def test_patient_pair_masks_and_conservative_demography():
    a=patient("FEMALE","WHITE","NOT HISPANIC OR LATINO",
              1,0,0,1,0)
    assert (a["CT_HEAD_imp"],a["CT_HEAD_day0"])==(0,1)
    assert a["any_day0"]==1
    assert a["any_imp"]==0
    assert a["advanced_day0"]==0
    assert a["age_band"]=="25TO34"
    assert a["ethnicity"]=="NOT_HISPANIC_LATINO"
    b=patient("M","BLACK","HISPANIC",0,1,1,1,1)
    assert b["MRI_BRAIN_imp"]==b["MRI_BRAIN_day0"]==1
    assert b["CT_HEAD_imp"]==1
    assert b["advanced_imp"]==1
    assert b["race"]=="BLACK_AFRICAN_AMERICAN"


def test_aggregate_is_paired_and_source_reconciled():
    data=[patient("FEMALE","WHITE","HISPANIC",0,0,1,1),
          patient("FEMALE","WHITE","HISPANIC",0,0,0,1),
          patient("FEMALE","WHITE","HISPANIC",0,0,0,0),
          patient("MALE","WHITE","HISPANIC",1,1,0,1)]
    t=s82.group_rows(data)
    ref={"patient_cohort_aggregates":{
        "COHORT|"+s82.PRIMARY:{"n":4,"imp":1,"new_day0_other":2}}}
    assert s82.verify(t,ref)
    assert int(t.n.sum())==4
    assert int(t.any_imp.sum())==1
    assert int(t.any_day0.sum())==3
    assert len(t)<=2


def test_fail_on_changed_frozen_capture_totals():
    t=s82.group_rows([patient("FEMALE","WHITE","HISPANIC",0,0,1,1)])
    ref={"patient_cohort_aggregates":{
        "COHORT|"+s82.PRIMARY:{"n":1,"imp":1,"new_day0_other":1}}}
    with pytest.raises(ValueError,match="frozen Step68"):
        s82.verify(t,ref)


def test_duplicated_or_non_nested_rows_fail():
    x=patient("MALE","WHITE","HISPANIC",0,1,1,1)
    x["CT_HEAD_day0"]=0
    with pytest.raises(ValueError,match="Non-nested"):
        s82.group_rows([x])


def test_nominal_paired_gain_difference_uses_discordant_events():
    rows=[]
    def add(level,n,imp,day):
        for i in range(n):
            rows.append(patient(level,"WHITE","HISPANIC",i%2,i%3==0,
                 int(i<imp),int(i<day)))
    add("FEMALE",100,50,70)
    add("MALE",100,40,80)
    table=s82.group_rows(rows)
    ans=s82.raw_pair(table,"sex","FEMALE","MALE","CT_HEAD")
    assert ans is not None
    assert ans["rd_imp"]==pytest.approx(-10)
    assert ans["rd_day"]==pytest.approx(10)
    assert ans["change"]==pytest.approx(20)
    # 40/100 vs 20/100 gains; independent nominal binomial variance.
    se=100*math.sqrt(.4*.6/100+.2*.8/100)
    assert ans["ci"]==pytest.approx((20-1.95996398454*se,20+1.95996398454*se))


def test_event_and_complement_screen_includes_newly_captured():
    assert s82.well_supported(100,30,60)
    assert not s82.well_supported(100,30,35)
    assert not s82.well_supported(100,95,97)
    assert not s82.well_supported(100,0,50)
    assert not s82.well_supported(100,20,100)


def test_sparse_quality_intersections_withheld():
    rows=[]
    for sex in ("MALE","FEMALE"):
        for p in (0,1):
            for held in (0,1):
                n=10 if sex=="MALE" and held==1 and p==1 else 20
                rows.extend(patient(sex,"WHITE","HISPANIC",p,held,1,1)
                            for _ in range(n))
    table=s82.group_rows(rows)
    assert not s82.adequate_quality(table,"sex","FEMALE","MALE")


def test_unsupported_outcome_and_no_pseudoprocedure_validation():
    table=s82.group_rows([patient("MALE","WHITE","HISPANIC",1,0,1,1)])
    with pytest.raises(ValueError,match="Unexpected analysis outcome"):
        s82.fitted(table,"Thrombectomy_flag","quality")
    with pytest.raises(ValueError,match="Invalid model scope"):
        s82.fitted(table,"CT_HEAD_imp","clinical_care")
