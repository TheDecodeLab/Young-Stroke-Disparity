"""Synthetic-only tests: none of the values come from the study export."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("step88", ROOT / "scripts/step88_paired_demographic_rule_contrasts.py")
step88 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = step88
spec.loader.exec_module(step88)


def fabricated():
    rows=[]
    for sex in ("MALE","FEMALE"):
      for race in ("WHITE","BLACK_AFRICAN_AMERICAN","UNKNOWN_MISSING"):
       for eth in ("NOT_HISPANIC_LATINO","HISPANIC_LATINO"):
        for year in ("2020","2021"):
         for age in ("25TO34","35TO44"):
          for p in (0,1):
           for held in (0,1):
            n=90
            # Every covariate affects baseline and/or incremental code capture.
            imp=round(n*(.22+.03*(sex=="FEMALE")+.04*(race=="BLACK_AFRICAN_AMERICAN")+.02*p+.01*held))
            gain=round(n*(.25+.04*(eth=="HISPANIC_LATINO")-.015*(race=="BLACK_AFRICAN_AMERICAN")+.01*p))
            d={"sex":sex,"race":race,"ethnicity":eth,"year":year,
                "age_band":age,"P":p,"held":held,"n":n,
                "any_imp":imp,"any_day0":imp+gain,
                "advanced_imp":round(.6*imp),"advanced_day0":round(.6*imp)+round(.6*gain)}
            rows.append(d)
    return pd.DataFrame(rows)


def test_nested_paired_counts_are_exact():
    x=step88.scoped(fabricated(),"quality")
    p=step88.joint_counts(x,"any")
    assert np.array_equal(p.sum(axis=1),x.n.to_numpy())
    assert np.array_equal(p[:,2],x.any_imp.to_numpy())
    assert np.array_equal(p[:,1]+p[:,2],x.any_day0.to_numpy())
    assert np.all(p>=0)


def test_patient_equivalent_bootstrap_preserves_pairing_and_bounds():
    x=fabricated()
    result=step88.analyze(x,"any","quality",draws=19,seed=53)
    assert result["valid_bootstraps"]==19
    assert len(result["comparisons"])==3
    for c in result["comparisons"]:
        vals=[c[name]["estimate"] for name in
              ("rule1_reference_pct","rule1_target_pct","rule2_reference_pct","rule2_target_pct")]
        assert all(0<=v<=100 for v in vals)
        assert c["rule2_RD_pp"]["estimate"]-c["rule1_RD_pp"]["estimate"] == pytest.approx(c["change_RD_pp"]["estimate"])
        assert c["change_RD_pp"]["ci_low"]<c["change_RD_pp"]["ci_high"]
        assert len(c["change_sensitivity_intervals"])==4


def test_complete_case_scope_excludes_only_unmapped_records():
    t=fabricated()
    x=step88.scoped(t,"complete_demographics")
    assert len(x)<len(t)
    assert (x.race!="UNKNOWN_MISSING").all()
    result=step88.analyze(t,"any","complete_demographics",draws=19,seed=8)
    assert result["cohort_n"]==int(x.n.sum())


def test_invalid_nesting_fails_closed():
    x=fabricated()
    x.loc[0,"any_day0"]=x.loc[0,"any_imp"]-1
    with pytest.raises(ValueError,match="nesting"):
        step88.joint_counts(x,"any")


def test_unsupported_and_unstable_models_fail_closed():
    x=fabricated()
    x.loc[x.sex=="FEMALE","any_imp"]=0
    x.loc[x.sex=="FEMALE","any_day0"]=0
    assert not step88.compatible_support(x,step88.joint_counts(x,"any"),"sex","MALE","FEMALE")
    with pytest.raises(ValueError,match="No disclosure-safe comparisons"):
        step88.analyze(x,"any","quality",draws=19,seed=8,comparisons=(("sex","MALE","FEMALE"),))


def test_scope_and_bootstrap_limits_are_enforced():
    t=fabricated()
    with pytest.raises(ValueError,match="scope"):
        step88.scoped(t,"unverified_scope")
    with pytest.raises(ValueError,match="Bootstrap"):
        step88.analyze(t,"any","quality",draws=2,seed=8)


def test_private_output_cannot_write_to_public_location(tmp_path):
    with pytest.raises(ValueError,match="private"):
        step88.save_private(tmp_path/"notallowed.json",{"synthetic":True})