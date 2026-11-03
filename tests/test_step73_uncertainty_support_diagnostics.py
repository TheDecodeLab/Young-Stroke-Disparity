"""Step73 fabricated-only GLM uncertainty, source-support and privacy checks."""
from itertools import product
from math import exp

import numpy as np
import pandas as pd
import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step72_exploratory_demographic_models as s72
from scripts import step73_uncertainty_support_diagnostics as s73


def fabricated_table():
    rows=[]
    for cohort,year,band,sex,race,eth,P,held in product(
            s62.COHORTS,("2018","2024"),("25TO34","35TO44"),
            ("MALE","FEMALE"),("WHITE","BLACK_AFRICAN_AMERICAN","ASIAN",
                                 "AIAN","NHPI"),
            ("NOT_HISPANIC_LATINO","HISPANIC_LATINO"),(0,1),(0,1)):
        score=(-0.2 + .18*(sex=="FEMALE")-.17*(race!="WHITE")
               +.12*(eth=="HISPANIC_LATINO")+.06*(year=="2024")
               +.03*(band=="35TO44")-.21*P-.16*held)
        n=60
        imp=int(round(n/(1+exp(-score))))
        advanced=max(0,imp-5)
        same=min(n,imp+9)
        rows.append(dict(cohort=cohort,year=year,age_band=band,sex=sex,
                         race=race,ethnicity=eth,P=P,held=held,n=n,
                         imp_any=imp,imp_advanced=advanced,
                         same_day_any=same,
                         same_day_advanced=min(n,advanced+8),
                         CT_HEAD_imp=imp-2,MRI_BRAIN_imp=advanced-2,
                         CTA_HEAD_imp=advanced-3))
    return pd.DataFrame(rows)


def test_marginal_effect_agrees_with_step72_independent_implementation():
    df=fabricated_table()
    old=s72.fit_one(df,s62.COHORTS[0],"imp_any","quality")
    model,x=s73.fit(df,s62.COHORTS[0],"imp_any","quality")
    assert model.converged
    for field,ref,level in s73.TARGETS:
        legacy=next(c for c in old["contrasts"]
                    if c[0]==field and c[1]==ref and c[2]==level)
        newer=s73.contrast(model,x,field,ref,level)
        assert newer["reference_pct"]==pytest.approx(legacy[4],abs=1e-8)
        assert newer["target_pct"]==pytest.approx(legacy[5],abs=1e-8)
        assert newer["difference_pp"]==pytest.approx(legacy[6],abs=1e-8)
        assert np.isfinite(newer["nominal_SE_pp"])
        assert newer["nominal_SE_pp"]>=0
        assert (newer["nominal_CI_low_pp"]<=newer["difference_pp"]
                <=newer["nominal_CI_high_pp"])


def test_delta_method_gradient_agrees_with_finite_difference():
    df=fabricated_table()
    model,x=s73.fit(df,s62.COHORTS[0],"imp_any","quality")
    exact=s73.contrast(model,x,"sex","MALE","FEMALE")
    from patsy import build_design_matrices
    from scipy.special import expit
    info=model.model.data.design_info
    beta=model.params.to_numpy(dtype=float)
    a=x.copy();a["sex"]="MALE"
    b=x.copy();b["sex"]="FEMALE"
    X0=np.asarray(build_design_matrices([info],a)[0],float)
    X1=np.asarray(build_design_matrices([info],b)[0],float)
    w=x.n.to_numpy(float)
    def margin(v):
        return 100*np.average(expit(X1@v)-expit(X0@v),weights=w)
    numerical=[]
    eps=1e-5
    for i in range(len(beta)):
        bp=beta.copy();bm=beta.copy()
        bp[i]+=eps;bm[i]-=eps
        numerical.append((margin(bp)-margin(bm))/(2*eps))
    observed=float(np.asarray(numerical)@model.cov_params().to_numpy()
                   @np.asarray(numerical))
    assert exact["nominal_SE_pp"]**2==pytest.approx(observed,abs=1e-7)


def test_source_support_reports_sparse_and_missing_P_cells():
    df=fabricated_table()
    x=s72.subset(df,s62.COHORTS[0],"quality")
    full=s73.support(x,"race","WHITE","NHPI")
    assert full["missing"]==0 and full["sparse"]==0
    depleted=x.loc[~((x.race=="NHPI")&(x.P==1)&(x.held==1))]
    q=s73.support(depleted,"race","WHITE","NHPI")
    assert q["missing"]==1 and q["sparse"]>=1
    assert q["total_cells"]==4


def test_all_specs_and_scope_validation():
    works=list(s73.specs())
    assert len(works)==17
    assert len(set(works))==17
    assert s73.formula("clean_only").endswith("+P")
    assert "+held" in s73.formula("quality")
    assert "+P" not in s73.formula("demographic_only")
    with pytest.raises(ValueError,match="Unsupported"):
        s73.formula("SOME_INVALID_SCOPE")


def test_unavailable_reference_or_no_support_fails():
    df=fabricated_table()
    model,x=s73.fit(df,s62.COHORTS[0],"imp_any","quality")
    with pytest.raises(ValueError,match="absent"):
        s73.contrast(model,x,"race","WHITE","NOT_A_REAL_CATEGORY")
    with pytest.raises(ValueError,match="predefined demographics"):
        s73.contrast(model,x,"patient","WHITE","NHPI")
