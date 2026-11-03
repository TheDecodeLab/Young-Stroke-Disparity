#!/usr/bin/env python3
"""Step73: local-only grouped-model precision and overlap diagnostics.

Uses the completed frozen Step62/63/68 SQLite checkpoints.
Working-binomial delta-method 95% intervals DO NOT account for
institution/HCO clustering, case mix, or differential outcome coding.
No row-level model input or patient identifiers are written.
"""
from __future__ import annotations

from collections import Counter
from math import sqrt
import json
import sqlite3
import warnings

import numpy as np
from patsy import build_design_matrices
from scipy.special import expit
import statsmodels.api as sm
import statsmodels.formula.api as smf

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
    from scripts import step68_joint_imaging_window_scan as s68
    from scripts import step72_exploratory_demographic_models as s72
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64
    import step68_joint_imaging_window_scan as s68
    import step72_exploratory_demographic_models as s72

TARGETS=(
    ("sex","MALE","FEMALE"),
    ("race","WHITE","BLACK_AFRICAN_AMERICAN"),
    ("race","WHITE","ASIAN"),
    ("race","WHITE","AIAN"),
    ("race","WHITE","NHPI"),
    ("ethnicity","NOT_HISPANIC_LATINO","HISPANIC_LATINO"),
)
CATEGORIES=("sex","race","ethnicity")


def formula(scope):
    if scope not in s72.SCOPES:
        raise ValueError("Unsupported model scope")
    f="rate ~ C(sex)+C(race)+C(ethnicity)+C(year)+C(age_band)"
    if scope!="demographic_only":
        f+="+P"
    if scope in ("quality","complete_demographics"):
        f+="+held"
    return f


def support(x,field,reference,target):
    """Report P x quarantine overlap by source-demographic group.

    For clean-only, P is still stratified while held is always 0.
    This is a positivity/measurement-structure diagnostic, not
    clinical overlap on unmeasured confounders.
    """
    subset=x.loc[x[field].isin((reference,target))]
    rows={}
    for label in (reference,target):
        t=subset.loc[subset[field]==label]
        per={(int(p),int(h)):int(t.loc[(t.P==p)&(t.held==h),"n"].sum())
             for p in (0,1) for h in sorted(set(x.held))}
        rows[label]=per
    cell_keys=sorted(set(rows[reference])|set(rows[target]))
    missing=sum(1 for key in cell_keys if (
        rows[reference].get(key,0)==0 or rows[target].get(key,0)==0))
    sparse=sum(1 for key in cell_keys if (
        min(rows[reference].get(key,0),rows[target].get(key,0))<11))
    min_nonzero=min((n for row in rows.values() for n in row.values()
                     if n>0),default=0)
    return {"missing":missing,"sparse":sparse,
            "total_cells":len(cell_keys),"min_nonzero":min_nonzero}


def fit(table,cohort,outcome,scope):
    if outcome not in s72.OUTCOMES:
        raise ValueError("Unsupported code-capture outcome")
    x=s72.subset(table,cohort,scope)
    if int(x.n.sum())<100:
        raise ValueError("Too few cohort memberships for grouped model")
    x["rate"]=x[outcome]/x.n
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model=smf.glm(formula(scope),data=x,
                      family=sm.families.Binomial(),
                      var_weights=x.n).fit(maxiter=100,disp=False)
    if (not model.converged or not np.isfinite(model.params).all()
            or np.max(np.abs(model.params))>24
            or not np.isfinite(model.cov_params().to_numpy()).all()):
        raise ValueError("Non-converged / poorly estimated grouped model")
    if any("PerfectSeparation" in type(w.message).__name__
           for w in caught):
        raise ValueError("Perfect separation detected")
    return model,x


def contrast(model,x,field,reference,target):
    if field not in CATEGORIES:
        raise ValueError("Only predefined demographics may be compared")
    if reference not in set(x[field]) or target not in set(x[field]):
        raise ValueError("Reference or target absent from the source sample")
    info=model.model.data.design_info
    weighted=x.n.to_numpy(dtype=float)
    n=weighted.sum()
    beta=model.params.to_numpy(dtype=float)
    data0=x.copy();data0[field]=reference
    data1=x.copy();data1[field]=target
    mat0=np.asarray(build_design_matrices([info],data0)[0],dtype=float)
    mat1=np.asarray(build_design_matrices([info],data1)[0],dtype=float)
    prob0=expit(mat0@beta)
    prob1=expit(mat1@beta)
    p0=float(100*np.dot(weighted,prob0)/n)
    p1=float(100*np.dot(weighted,prob1)/n)
    diff=p1-p0
    grad0=100*np.sum((weighted*prob0*(1-prob0))[:,None]*mat0,axis=0)/n
    grad1=100*np.sum((weighted*prob1*(1-prob1))[:,None]*mat1,axis=0)/n
    grad=grad1-grad0
    var=float(grad@model.cov_params().to_numpy(dtype=float)@grad)
    if not np.isfinite(var) or var < -1e-8:
        raise ValueError("Nonfinite or negative delta-method variance")
    se=sqrt(max(var,0))
    nref=int(x.loc[x[field]==reference,"n"].sum())
    ntarget=int(x.loc[x[field]==target,"n"].sum())
    if nref<11 or ntarget<11:
        raise ValueError("Demographic comparison below aggregate minimum")
    return {
        "n_target":ntarget,"n_reference":nref,
        "reference_pct":p0,"target_pct":p1,
        "difference_pp":diff,
        "nominal_CI_low_pp":diff-1.959963984540054*se,
        "nominal_CI_high_pp":diff+1.959963984540054*se,
        "nominal_SE_pp":se,
        "support":support(x,field,reference,target)
    }


def specs():
    for cohort in s62.COHORTS:
        for y in ("imp_any","imp_advanced","same_day_any","same_day_advanced"):
            yield cohort,y,"quality"
    for scope in ("demographic_only","clean_only","complete_demographics"):
        for y in ("imp_any","same_day_any"):
            yield s72.PRIMARY,y,scope
    for y in ("CT_HEAD_imp","MRI_BRAIN_imp","CTA_HEAD_imp"):
        yield s72.PRIMARY,y,"quality"


def output(table):
    print("STEP73 LOCAL ONLY: NOMINAL working-binomial 95% interval and overlap audit")
    print("Intervals are NOT HCO-cluster-robust, NOT causal, and NOT validated radiology utilization.")
    print("Reference-standardized contrasts are descriptive; assume fitted GLM and independent patients.")
    print("NO significance claims; severity, HCO selection and coding completeness unobserved.")
    print("MISSING/sparse P x quarantine cells imply extrapolation risk.")
    failed=0
    for cohort,y,scope in specs():
        print("\nMODEL",cohort,y,scope,flush=True)
        try:
            model,x=fit(table,cohort,y,scope)
        except (ValueError,RuntimeError,np.linalg.LinAlgError):
            print("  MODEL_UNAVAILABLE; no estimates")
            failed+=1
            continue
        dev_ratio=float(model.deviance/model.df_resid) if model.df_resid>0 else float("nan")
        print("  n",int(x.n.sum()),"strata",len(x),
              "converged",bool(model.converged),
              "deviance_per_grouped_residual_df","%.2f"%dev_ratio)
        for field,ref,target in TARGETS:
            try:
                t=contrast(model,x,field,ref,target)
            except (ValueError,RuntimeError,np.linalg.LinAlgError):
                print("  ",field,target,"vs",ref,"UNAVAILABLE")
                failed+=1
                continue
            q=t["support"]
            print("  ",field,target,"vs",ref,
                  "n",t["n_target"],
                  "RD_pp","%+.2f"%t["difference_pp"],
                  "NOMINAL_95CI_pp","[%+.2f,%+.2f]"%
                    (t["nominal_CI_low_pp"],t["nominal_CI_high_pp"]),
                  "P_quarantine_support_missing_cells",q["missing"],
                  "sparse_cells_lt11",q["sparse"],
                  "total_cells",q["total_cells"],
                  "min_nonzero_cell",q["min_nonzero"])
    print("\nSTEP73_MODEL_OR_COMPARISON_FAILURES",failed)
    if failed:
        raise ValueError("Some Step73 models or targeted contrasts unavailable")


def main():
    paths=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    for p in paths:
        if p.is_symlink() or not p.is_file():
            raise FileNotFoundError("Frozen private SQL source database missing")
    p62,p63,p68=(p.resolve() for p in paths)
    report=s68.PRIVATE/s68.REPORT
    if report.is_symlink() or not report.is_file():
        raise FileNotFoundError("Step68 aggregate reference missing")
    reference=json.loads(report.read_text(encoding="utf-8"))
    if reference.get("stage")!=s68.POLICY:
        raise ValueError("Step68 policy mismatch")
    with sqlite3.connect("file:"+str(p63)+"?mode=ro",uri=True) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:"+str(p62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",
                   ("file:"+str(p68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,p62,p63)
        frozen=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if frozen is None:
            raise ValueError("Step68 snapshot missing")
        meta=json.loads(frozen[0])
        if (meta.get("policy")!=s68.POLICY
                or meta.get("s62")!=s68._snapshot(p62)
                or meta.get("s63")!=s68._snapshot(p63)):
            raise ValueError("Step68 input snapshot mismatch")
        status=db.execute(
            "SELECT seen,done FROM capture.progress WHERE stage='procedure'"
        ).fetchone()
        if status != (993025015,1):
            raise ValueError("Step68 procedure scan not complete")
        table=s72.build(db)
        s72.verify(table,reference)
        output(table)
    print("\nHANDOFF: TERMINAL OUTPUT ONLY. No ZIP or private results files.")


if __name__=="__main__":
    main()
