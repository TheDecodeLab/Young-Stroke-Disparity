#!/usr/bin/env python3
"""Step82: local-only demographic sensitivity to CPT14 encounter attribution.

Uses immutable Step62/63/68 checkpoints. One read-only indexed-patient
stream is grouped in memory; no patient identifiers or records are exported.
Analysis is exploratory and cannot identify clinical imaging disparities.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import closing
from math import sqrt
import json
import sqlite3
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
    from scripts import step68_joint_imaging_window_scan as s68
    from scripts import step71_demographic_capture_feasibility as s71
    from scripts import step73_uncertainty_support_diagnostics as s73
    from scripts import step81_frozen_modality_demographic_gate as s81
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64
    import step68_joint_imaging_window_scan as s68
    import step71_demographic_capture_feasibility as s71
    import step73_uncertainty_support_diagnostics as s73
    import step81_frozen_modality_demographic_gate as s81

PRIMARY=s62.COHORTS[0]
COVS=("sex","race","ethnicity","year","age_band","P","held")
MODALITIES=("CT_HEAD","MRI_BRAIN","CTA_HEAD")
OUTCOMES=("any","advanced","CT_HEAD","MRI_BRAIN","CTA_HEAD")
DEFS=("imp","day0")
CONTRASTS=(
    ("sex","FEMALE","MALE"),
    ("race","WHITE","BLACK_AFRICAN_AMERICAN"),
    ("ethnicity","NOT_HISPANIC_LATINO","HISPANIC_LATINO"),
)
MISSING={"UNKNOWN_MISSING","OTHER_OR_UNMAPPED"}
MIN=11
EXPECTED_PROCEDURE_ROWS=993025015


def classify_record(info,mods):
    """Map one local indexed member to allowed coarse fields and paired flags."""
    cohort,yr,P,yob,sex,race,ethnicity,held=info
    if cohort!=PRIMARY:
        return None
    y=int(yr)
    if yob is None or not (1900<=int(yob)<=y):
        raise ValueError("Invalid indexed birth year")
    upper=y-int(yob)
    if not 18<=upper<=56:
        raise ValueError("Indexed birth-year proxy outside supported bounds")
    age_band=("UNDER25" if upper<25 else "25TO34" if upper<35
              else "35TO44" if upper<45 else "45PLUS")
    row={
        "sex":s71.category("SEX",sex),
        "race":s71.category("RACE",race),
        "ethnicity":s71.category("ETHNICITY",ethnicity),
        "year":str(y),"age_band":age_band,"P":int(P),"held":int(held)
    }
    all_mask=0
    adv_mask=0
    for m,b in mods.items():
        if m not in s81.MODALITIES:
            raise ValueError("Modality outside 14-code dictionary")
        all_mask |= b
        if m in s71.ADVANCED:
            adv_mask |= b
    masks={"any":all_mask,"advanced":adv_mask}
    masks.update({m:mods.get(m,0) for m in MODALITIES})
    for label,mask in masks.items():
        row[label+"_imp"]=int(bool(mask&s68.IMP))
        row[label+"_day0"]=int(bool(mask&(s68.IMP|s68.NONIMP_DAY0)))
        if row[label+"_imp"]>row[label+"_day0"]:
            raise ValueError("Indexed capture missing from same-day union")
    return row


def stream(db):
    """Patient-keyed SQL stream consumed locally; patient key never returned."""
    sql="""
    SELECT i.cohort,i.patient,substr(i.start,1,4),i.principal,
           p.yob,p.sex,p.race,p.ethnicity,
           CASE WHEN EXISTS(
             SELECT 1 FROM main.ambiguous a WHERE a.patient=i.patient
           ) THEN 1 ELSE 0 END,
           f.modality,f.mask
    FROM main.idx i
    LEFT JOIN baseline.person p ON p.patient=i.patient
    LEFT JOIN capture.flags f
      ON f.cohort=i.cohort AND f.patient=i.patient
    WHERE i.cohort=?
    ORDER BY i.cohort,i.patient
    """
    prior=None
    info=None
    mods={}
    for cohort,person,year,P,yob,sex,race,ethnicity,held,modality,mask in db.execute(sql,(PRIMARY,)):
        key=(cohort,person)
        if key!=prior:
            if info is not None:
                yield classify_record(info,mods)
            prior=key
            info=(cohort,year,P,yob,sex,race,ethnicity,held)
            mods={}
        if modality is not None:
            if modality in mods:
                raise ValueError("Duplicated patient/cohort/modality")
            mods[modality]=int(mask)
    if info is not None:
        yield classify_record(info,mods)


def group_rows(records):
    """Collapse locally to covariate strata; never create row-level export."""
    out=defaultdict(Counter)
    endcols=[x+"_"+d for x in ("any","advanced")+MODALITIES for d in DEFS]
    for row in records:
        if row is None:
            continue
        key=tuple(row[k] for k in COVS)
        c=out[key]
        c["n"]+=1
        for col in endcols:
            c[col]+=int(row[col])
    if not out:
        raise ValueError("Empty primary cohort")
    table=pd.DataFrame([{**dict(zip(COVS,k)),**c} for k,c in out.items()])
    for x in ("n",)+tuple(endcols):
        table[x]=table[x].fillna(0).astype(int)
        if not (table[x].ge(0)).all():
            raise ValueError("Negative grouped count")
        if x!="n" and not (table[x].le(table.n)).all():
            raise ValueError("Outcome exceeds stratum denominator")
    for x in ("any","advanced")+MODALITIES:
        if not (table[x+"_imp"]<=table[x+"_day0"]).all():
            raise ValueError("Non-nested indexed and same-day indicators")
    return table


def verify(table,ref):
    n=int(table.n.sum())
    expected=ref["patient_cohort_aggregates"]["COHORT|"+PRIMARY]
    if (n!=int(expected["n"]) or
        int(table.any_imp.sum())!=int(expected["imp"]) or
        int(table.any_day0.sum())!=int(expected["imp"])+int(expected["new_day0_other"])):
        raise ValueError("Step82 grouped patient totals fail frozen Step68 reconciliation")
    for field in ("sex","race","ethnicity","year","P","held"):
        if int(table.groupby(field,dropna=False).n.sum().sum())!=n:
            raise ValueError("Incomplete grouped covariate partition")
    if not (table.advanced_imp<=table.any_imp).all() or not (
        table.advanced_day0<=table.any_day0).all():
        raise ValueError("Advanced not contained in any imaging")
    return True


def totals(table,field,level,outcome):
    x=table.loc[table[field]==level]
    return (int(x.n.sum()),int(x[outcome+"_imp"].sum()),
            int(x[outcome+"_day0"].sum()))


def well_supported(n,index,day):
    """Suppress cells or complements <=10, including newly gained codes."""
    return (n>=2*MIN and MIN<=index<=n-MIN
            and MIN<=day<=n-MIN
            and MIN<=day-index<=n-MIN)


def raw_pair(table,field,reference,target,outcome):
    n0,a0,b0=totals(table,field,reference,outcome)
    n1,a1,b1=totals(table,field,target,outcome)
    if not (well_supported(n0,a0,b0) and well_supported(n1,a1,b1)):
        return None
    rd_imp=100*(a1/n1-a0/n0)
    rd_day=100*(b1/n1-b0/n0)
    diff_gain=100*((b1-a1)/n1-(b0-a0)/n0)
    p1=(b1-a1)/n1
    p0=(b0-a0)/n0
    se=100*sqrt(p1*(1-p1)/n1+p0*(1-p0)/n0)
    z=1.95996398454
    return dict(rd_imp=rd_imp,rd_day=rd_day,change=diff_gain,
                ci=(diff_gain-z*se,diff_gain+z*se))


def adequate_quality(table,field,reference,target):
    """Require mapped categories and P x ambiguity strata to be non-sparse.

    This is not a hospital-overlap test. It does not prove representativeness.
    """
    if reference in MISSING or target in MISSING:
        return False
    part=table.loc[table[field].isin((reference,target))]
    if set(part[field])!={reference,target}:
        return False
    for p in (0,1):
        for h in (0,1):
            for level in (reference,target):
                if int(part.loc[(part.P==p)&(part.held==h)&
                                (part[field]==level),"n"].sum())<MIN:
                    return False
    return True


def scope_support(table,field,reference,target,scope):
    """Require adequate P x ambiguity support *within the requested scope*.

    P=0 is structurally absent in a P1-only model; held=1 is absent
    in a clean-only model. Neither should count as a sparse cell.
    Conversely, both groups must have >=11 members in each applicable
    P/ambiguity stratum. Does not verify HCO overlap.
    """
    if field not in ("sex","race","ethnicity") or (
            reference in MISSING or target in MISSING or reference==target):
        return False
    allowed={
        "quality":((0,1),(0,1)),
        "P1":((1,),(0,1)),
        "clean":((0,1),(0,))
    }
    if scope not in allowed:
        raise ValueError("Unsupported scope for overlap checks")
    ps,hs=allowed[scope]
    if not set(table.P.unique()).issubset(ps) or not (
            set(table.held.unique()).issubset(hs)):
        raise ValueError("Scope contains disallowed P/ambiguity strata")
    for p in ps:
        for h in hs:
            for label in (reference,target):
                n=int(table.loc[(table.P==p)&(table.held==h)&
                                (table[field]==label),"n"].sum())
                if n<MIN:
                    return False
    return True


def fitted(table,outcome,scope):
    if outcome not in [x+"_"+d for x in OUTCOMES for d in DEFS]:
        raise ValueError("Unexpected analysis outcome")
    x=table.copy()
    if scope=="P1":
        x=x.loc[x.P==1].copy()
    elif scope=="clean":
        x=x.loc[x.held==0].copy()
    elif scope!="quality":
        raise ValueError("Invalid model scope")
    if x.empty or int(x.n.sum())<200:
        raise ValueError("Insufficient indexed members")
    x["rate"]=x[outcome]/x.n
    form="rate ~ C(sex)+C(race)+C(ethnicity)+C(year)+C(age_band)"
    if scope!="P1":
        form+="+P"
    if scope!="clean":
        form+="+held"
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        model=smf.glm(formula=form,data=x,
                      family=sm.families.Binomial(),
                      var_weights=x.n).fit(maxiter=100,disp=False)
    if (not model.converged or not np.isfinite(model.params).all()
            or not np.isfinite(model.cov_params().to_numpy()).all()
            or np.max(np.abs(model.params))>24
            or any("PerfectSeparation" in type(w.message).__name__
                   for w in rec)):
        raise ValueError("Nonconverged, unstable or separated grouped model")
    return model,x


def run_summary(table):
    print("STEP82 LOCAL ONLY: paired demographic ascertainment sensitivity")
    print("Recorded codes only; no inferred completed scans or care disparities.")
    print("Adjusted CIs assume grouped-binomial independent patients, NOT HCO clustering.")
    print("Paired change CI uses observed newly captured patient flag (nominal only).")
    print("Category counts/rates and small or complementary events not printed.")
    print("Scope QUALITY adjusts age-band, calendar year, P, ambiguity, other demographics.")
    print("Sensitivities P1 (flagged principal), CLEAN (no ambiguous encounter keys).")
    for outcome in OUTCOMES:
        for field,ref,alt in CONTRASTS:
            label=outcome+" "+field+" "+alt+"_vs_"+ref
            if not adequate_quality(table,field,ref,alt):
                print("PRIMARY",label,"WITHHELD: sparse recording-quality support")
                continue
            pair=raw_pair(table,field,ref,alt,outcome)
            if pair is None:
                print("PRIMARY",label,"WITHHELD: event/complement disclosure gate")
                continue
            print("RAW",label,"inpatient_RD_pp",("%+.2f"%pair["rd_imp"]),
                  "same_day_RD_pp",("%+.2f"%pair["rd_day"]),
                  "change_pp",("%+.2f"%pair["change"]),
                  "nominal_95CI_change_pp","[%+.2f,%+.2f]"%pair["ci"])
    for scope in ("quality","P1","clean"):
        print("ADJUSTED_SCOPE",scope)
        for outcome in OUTCOMES:
            for definition in DEFS:
                end=outcome+"_"+definition
                try:
                    model,x=fitted(table,end,scope)
                except (ValueError,RuntimeError,np.linalg.LinAlgError):
                    print("MODEL",end,"UNAVAILABLE: numerical/overlap stability")
                    continue
                for field,ref,alt in CONTRASTS:
                    label=end+" "+field+" "+alt+"_vs_"+ref
                    if not scope_support(x,field,ref,alt,scope):
                        print("CONTRAST",label,"WITHHELD: sparse applicable P x ambiguity support")
                        continue
                    a=totals(x,field,ref,outcome)
                    b=totals(x,field,alt,outcome)
                    if not (a[0] and b[0]):
                        print("CONTRAST",label,"WITHHELD: absent category")
                        continue
                    a_event=int(x.loc[x[field]==ref,end].sum())
                    b_event=int(x.loc[x[field]==alt,end].sum())
                    if not (MIN<=a_event<=a[0]-MIN and
                            MIN<=b_event<=b[0]-MIN):
                        print("CONTRAST",label,"WITHHELD: event/complement gate")
                        continue
                    try:
                        t=s73.contrast(model,x,field,ref,alt)
                    except (ValueError,RuntimeError,np.linalg.LinAlgError):
                        print("CONTRAST",label,"UNAVAILABLE: support/design matrix")
                        continue
                    # Step73's legacy diagnostic hard-codes P=(0,1), which
                    # incorrectly calls the P1-only source subset sparse.
                    # scope_support above enforces the applicable strata.
                    print("CONTRAST",label,
                          "adjusted_RD_pp","%+.2f"%t["difference_pp"],
                          "nominal_95CI_pp","[%+.2f,%+.2f]"%
                           (t["nominal_CI_low_pp"],t["nominal_CI_high_pp"]))
    print("ENCOUNTER-TYPE MECHANISM: UNRESOLVED WITH FROZEN CHECKPOINTS")
    print("Step63 stores EMER/IMP metadata only; Step68 stores modality-window")
    print("patient masks, not the actual non-index code-bearing encounter types.")
    print("Do not label other-same-day codes outpatient/radiology/ED without evidence.")
    print("TREATMENT-POSITIVE CONTROL: no patient-level treatment flags preserved.")
    print("NO source ZIP, procedure-file rescan, patient export, or institutional contact.")
    print("HANDOFF: terminal output only; institutional cross-table review still pending.")


def main():
    paths=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise FileNotFoundError("Frozen Step62/63/68 checkpoint missing")
    p62,p63,p68=(p.resolve() for p in paths)
    report=s68.PRIVATE/s68.REPORT
    if report.is_symlink() or not report.is_file():
        raise FileNotFoundError("Frozen Step68 aggregate missing")
    ref=json.loads(report.read_text(encoding="utf-8"))
    if ref.get("stage")!=s68.POLICY:
        raise ValueError("Step68 policy mismatch")
    with closing(sqlite3.connect("file:"+str(p63)+"?mode=ro",uri=True)) as db:
        db.execute("ATTACH DATABASE ? AS baseline",("file:"+str(p62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",("file:"+str(p68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,p62,p63)
        row=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if row is None:
            raise ValueError("Frozen Step68 input metadata absent")
        sig=json.loads(row[0])
        if (sig.get("policy")!=s68.POLICY or
            sig.get("s62")!=s68._snapshot(p62) or
            sig.get("s63")!=s68._snapshot(p63)):
            raise ValueError("Step68 source signatures disagree")
        seen=db.execute("SELECT seen,done FROM capture.progress "
                        "WHERE stage='procedure'").fetchone()
        if seen!=(EXPECTED_PROCEDURE_ROWS,1):
            raise ValueError("Step68 incomplete; source rescan forbidden")
        table=group_rows(stream(db))
        verify(table,ref)
    run_summary(table)


if __name__=="__main__":
    main()
