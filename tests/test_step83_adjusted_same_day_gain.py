"""Step83 fabricated-only tests: paired gains and scoped model checks."""
from itertools import product
import pandas as pd
import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step68_joint_imaging_window_scan as s68
from scripts import step73_uncertainty_support_diagnostics as s73
from scripts import step82_demographic_definition_sensitivity as s82
from scripts import step83_adjusted_same_day_gain as s83


def patient(mods):
    return s82.classify_record(
        (s62.COHORTS[0],"2020",1,1990,"FEMALE","WHITE",
         "NOT HISPANIC OR LATINO",0),mods)


def reference(n,imp,gain):
    return {"patient_cohort_aggregates":{
        "COHORT|"+s82.PRIMARY:{
            "n":n,"imp":imp,"new_day0_other":gain}}}


def test_modality_gain_can_occur_without_any_code_gain():
    # On index IMP, patient has CT. On another same-day record, MRI only.
    # MRI gets a newly attributed code, while ANY is already positive.
    x=s82.group_rows([patient({
        "CT_HEAD":s68.IMP,"MRI_BRAIN":s68.NONIMP_DAY0
    })])
    y=s83.gain_table(x,reference(1,1,0))
    assert int(y.any_gain.sum())==0
    assert int(y.MRI_BRAIN_gain.sum())==1
    assert int(y.CT_HEAD_gain.sum())==0


def test_gain_reconciles_to_frozen_new_day0_only():
    x=s82.group_rows([patient({"CT_HEAD":s68.NONIMP_DAY0})])
    y=s83.gain_table(x,reference(1,0,1))
    assert int(y.any_gain.sum())==1
    with pytest.raises(ValueError,match="frozen Step68"):
        s83.gain_table(x,reference(1,0,0))


def fabricated_grouped():
    rows=[]
    for sex,race,ethnicity,year,age,P,held in product(
        ("MALE","FEMALE"),("WHITE","BLACK_AFRICAN_AMERICAN"),
        ("HISPANIC_LATINO","NOT_HISPANIC_LATINO"),
        ("2019","2021"),("25TO34","35TO44"),(0,1),(0,1)
    ):
        n=60
        gain=16+4*(sex=="MALE")+3*(race=="BLACK_AFRICAN_AMERICAN") + (
            3 if ethnicity=="HISPANIC_LATINO" else 0) + int(P==1)
        rows.append(dict(sex=sex,race=race,ethnicity=ethnicity,
                         year=year,age_band=age,P=P,held=held,n=n,
                         CT_HEAD_gain=gain,any_gain=gain,
                         MRI_BRAIN_gain=gain,CTA_HEAD_gain=gain,
                         advanced_gain=gain))
    return pd.DataFrame(rows)


def test_scope_support_follows_actual_p_and_held_subsets():
    base=fabricated_grouped()
    ref,target="WHITE","BLACK_AFRICAN_AMERICAN"
    for scope in s83.SCOPES:
        x=s83.subset(base,scope)
        assert s83.overlap(x,"race",ref,target,scope)
        assert s83.has_event_complement(x,"race",ref,target,"CT_HEAD_gain")
        if scope=="P0":
            assert set(x.P)=={0}
        if scope=="P1":
            assert set(x.P)=={1}
        if scope=="clean":
            assert set(x.held)=={0}


def test_model_uses_gain_event_and_restricted_contrasts():
    table=fabricated_grouped()
    for scope in s83.SCOPES:
        x=s83.subset(table,scope)
        model,design=s83.model(x,"CT_HEAD_gain",scope)
        ans=s73.contrast(model,design,"race","WHITE",
                         "BLACK_AFRICAN_AMERICAN")
        assert ans["difference_pp"]>0
        assert (ans["nominal_CI_low_pp"]<
                ans["difference_pp"]<
                ans["nominal_CI_high_pp"])


def test_sparse_support_or_small_gain_withheld():
    table=fabricated_grouped()
    table.loc[(table.P==1)&(table.held==1)&(
        table.sex=="MALE"),"n"]=0
    assert not s83.overlap(table,"sex","FEMALE","MALE","P1")
    good=fabricated_grouped()
    good.loc[good.race=="BLACK_AFRICAN_AMERICAN",
             "CT_HEAD_gain"]=0
    assert not s83.has_event_complement(good,"race","WHITE",
                                        "BLACK_AFRICAN_AMERICAN",
                                        "CT_HEAD_gain")


def test_reject_unknown_model_outcome_and_scope():
    table=fabricated_grouped()
    with pytest.raises(ValueError,match="Unsupported"):
        s83.model(table,"thrombectomy_gain","quality")
    with pytest.raises(ValueError,match="Unsupported"):
        s83.subset(table,"outpatient")


def test_report_only_aggregate_completeness(capsys):
    table=fabricated_grouped()
    s83.quality_categories(table)
    out=capsys.readouterr().out
    assert "SOURCE DEMOGRAPHIC COMPLETENESS BY P" in out
    assert "patient_id" not in out
    assert "WHITE" not in out
