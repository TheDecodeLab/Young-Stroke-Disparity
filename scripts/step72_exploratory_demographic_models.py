#!/usr/bin/env python3
"""Step72: local-only exploratory demographic CPT14 coding associations.

One read-only pass through frozen Step62/63/68 SQLite checkpoints.
Grouped binomial GLMs with marginal-standardized CODE-CAPTURE rates,
not clinically verified imaging receipt or causal disparities.
No patient IDs or individual-level outputs are written or printed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
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
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64
    import step68_joint_imaging_window_scan as s68
    import step71_demographic_capture_feasibility as s71

PRIMARY=s62.COHORTS[0]
OUTCOMES=("imp_any","imp_advanced","same_day_any","same_day_advanced",
          "CT_HEAD_imp","MRI_BRAIN_imp","CTA_HEAD_imp")
SCOPES=("quality","demographic_only","clean_only","complete_demographics")
FIELDS=("sex","race","ethnicity","year","age_proxy","P","held")
COMPARE={
    "sex":("MALE",("FEMALE",)),
    "race":("WHITE",("BLACK_AFRICAN_AMERICAN","ASIAN","AIAN",
                    "NHPI","OTHER_OR_UNMAPPED","UNKNOWN_MISSING")),
    "ethnicity":("NOT_HISPANIC_LATINO",("HISPANIC_LATINO","UNKNOWN_MISSING")),
}


def records(db):
    """Yield one deidentified analytic observation per indexed cohort member.

    Stream join remains patient-keyed inside SQL/loop. We only yield approved
    broad category labels, bounded year/age proxy, binary quality markers
    and recorded-code indicators, never patient identifiers or raw labels.
    """
    query="""
    SELECT i.cohort,i.patient,substr(i.start,1,4),i.principal,
           p.yob,p.sex,p.race,p.ethnicity,
           CASE WHEN EXISTS(SELECT 1 FROM main.ambiguous a
                            WHERE a.patient=i.patient) THEN 1 ELSE 0 END,
           f.modality,f.mask
    FROM main.idx i
    LEFT JOIN baseline.person p ON p.patient=i.patient
    LEFT JOIN capture.flags f
      ON f.cohort=i.cohort AND f.patient=i.patient
    ORDER BY i.cohort,i.patient
    """
    previous=None
    info=None
    mods={}
    def finish():
        if info is None:
            return None
        cohort,year,P,yob,sex,race,ethnicity,held=info
        if yob is None or not (1900 <= int(yob) <= int(year)):
            raise ValueError("Step72 indexed member missing valid birth year")
        year=int(year)
        # Date-only birth YEAR makes exact age unknowable, so use proxy:
        # (year-of-index minus year-of-birth) in whole years, not actual age.
        upper=year-int(yob)
        if upper<18 or upper>56:
            raise ValueError("Implausible Step72 indexed age-year proxy")
        x={"cohort":cohort,"year":str(year),"age_proxy":upper,
           "sex":s71.category("SEX",sex),
           "race":s71.category("RACE",race),
           "ethnicity":s71.category("ETHNICITY",ethnicity),
           "P":int(P),"held":int(held)}
        m=s71.measure(mods,P,held)
        for name in OUTCOMES:
            x[name]=int(m[name])
        return x
    for cohort,person,year,P,yob,sex,race,ethnicity,held,modality,mask in db.execute(query):
        key=(cohort,person)
        if key!=previous:
            v=finish()
            if v is not None:
                yield v
            previous=key
            info=(cohort,year,P,yob,sex,race,ethnicity,held)
            mods={}
        if modality is not None:
            if modality in mods:
                raise ValueError("Step72 repeated patient/cohort modality")
            mods[modality]=int(mask)
    v=finish()
    if v is not None:
        yield v


def build(db):
    # Aggregate in memory by a finite, deidentified covariate combination.
    # No row-level patient file or identifier is retained or exported.
    accum=defaultdict(Counter)
    for x in records(db):
        key=tuple(x[f] for f in ("cohort",)+FIELDS)
        c=accum[key]
        c["n"]+=1
        for y in OUTCOMES:
            c[y]+=x[y]
    cols=("cohort",)+FIELDS
    table=pd.DataFrame([{**dict(zip(cols,key)),**v}
                        for key,v in accum.items()])
    if table.empty:
        raise ValueError("Step72 empty aggregated model design")
    for field in ("n",)+OUTCOMES:
        table[field]=table[field].astype(int)
    for field in ("P","held","age_proxy"):
        table[field]=table[field].astype(int)
    for field in ("cohort","sex","race","ethnicity","year"):
        table[field]=table[field].astype(str)
    return table


def verify(table,prior):
    if not set(OUTCOMES).issubset(table.columns):
        raise ValueError("Step72 missing outcome columns")
    for cohort in s62.COHORTS:
        part=table.loc[table.cohort==cohort]
        ref=prior["patient_cohort_aggregates"]["COHORT|"+cohort]
        expected={
            "n":"n","imp_any":"imp","same_day_any":"same_day_any",
            "imp_advanced":"not_available",
            "day0_new_any":"new_day0_other",
        }
        if part.empty:
            raise ValueError("Missing required Step72 cohort")
        if int(part.n.sum())!=int(ref["n"]):
            raise ValueError("Step72 denominator differs from Step68")
        if int(part.imp_any.sum())!=int(ref["imp"]):
            raise ValueError("Step72 inpatient CPT14 differs from Step68")
        if int(part.same_day_any.sum())!=int(ref["imp"])+int(ref["new_day0_other"]):
            raise ValueError("Step72 same-day union differs from Step68")
        if not all((part[y].ge(0)&part[y].le(part.n)).all() for y in OUTCOMES):
            raise ValueError("Step72 outcomes outside binomial bounds")
        if not (part.imp_advanced.sum() <= part.imp_any.sum() and
                part.same_day_advanced.sum() <= part.same_day_any.sum()):
            raise ValueError("Advanced composite not nested within any CPT14")
        for kind in ("sex","race","ethnicity","year","P","held"):
            if int(part.groupby(kind,dropna=False).n.sum().sum())!=int(ref["n"]):
                raise ValueError("Step72 covariate partition mismatch")
    return True


def subset(table, cohort, scope):
    x=table.loc[table.cohort==cohort].copy()
    if scope=="clean_only":
        x=x.loc[x.held==0].copy()
    elif scope=="complete_demographics":
        for field in ("sex","race","ethnicity"):
            x=x.loc[~x[field].isin(("UNKNOWN_MISSING","OTHER_OR_UNMAPPED"))].copy()
    elif scope not in ("quality","demographic_only"):
        raise ValueError("Unknown Step72 model scope")
    if x.empty:
        raise ValueError("Model restricted subset empty")
    return x


def fit_one(table,cohort,outcome,scope):
    if outcome not in OUTCOMES:
        raise ValueError("Unexpected outcome")
    x=subset(table,cohort,scope)
    if x.n.sum()<100:
        raise ValueError("Insufficient observations for aggregate modeling")
    x["rate"]=x[outcome]/x.n
    form=("rate ~ C(sex) + C(race) + C(ethnicity) + C(year) + age_proxy")
    if scope!="demographic_only":
        form+=" + P"
    if scope=="quality" or scope=="complete_demographics":
        form+=" + held"
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        fit=smf.glm(formula=form,data=x,family=sm.families.Binomial(),
                    var_weights=x.n).fit(maxiter=100,disp=False)
    if (not fit.converged or not np.isfinite(fit.params.to_numpy()).all()
            or max(abs(fit.params)) > 24):
        raise ValueError("Step72 GLM unstable or separation suspected")
    if any("PerfectSeparation" in type(w.message).__name__
           for w in ws):
        raise ValueError("Step72 GLM detected perfect separation")
    overall=int(x.n.sum())
    results={"cohort":cohort,"scope":scope,"outcome":outcome,
             "n":overall,"n_strata":len(x),
             "observed_pct":float(100*x[outcome].sum()/overall),
             "converged":bool(fit.converged),"contrasts":[]}
    for field,(ref,targets) in COMPARE.items():
        actual=set(x[field])
        if ref not in actual:
            continue
        for level in targets:
            if level not in actual:
                continue
            reference=x.copy()
            reference[field]=ref
            alternative=x.copy()
            alternative[field]=level
            p_ref=float(100*np.average(fit.predict(reference),weights=x.n))
            p_alt=float(100*np.average(fit.predict(alternative),weights=x.n))
            n_ref=int(x.loc[x[field]==ref,"n"].sum())
            n_alt=int(x.loc[x[field]==level,"n"].sum())
            if n_ref<11 or n_alt<11:
                continue
            results["contrasts"].append((field,ref,level,n_alt,
                                          p_ref,p_alt,p_alt-p_ref))
    if not results["contrasts"]:
        raise ValueError("Step72 no supported demographic comparisons")
    return results


def print_results(table):
    print("STEP72 LOCAL-ONLY: exploratory GLM-adjusted CPT14 code-capture screen")
    print("MARGINAL probabilities are point estimates only; no causal or imaging-performance claims.")
    print("No HCO variable. NO cluster-robust CI or p-values, no clinical disparity conclusion.")
    print("Missing demographics retained as explicit group; complete-case is a sensitivity.")
    print("Age uses year-of-birth YEAR proxy; exact age unavailable.")
    print("Unmeasured case mix and selection/coding effects may confound ALL results.")
    workloads=[]
    for cohort in s62.COHORTS:
        for outcome in ("imp_any","imp_advanced","same_day_any","same_day_advanced"):
            workloads.append((cohort,outcome,"quality"))
    for scope in ("demographic_only","clean_only","complete_demographics"):
        for outcome in ("imp_any","same_day_any"):
            workloads.append((PRIMARY,outcome,scope))
    for outcome in ("CT_HEAD_imp","MRI_BRAIN_imp","CTA_HEAD_imp"):
        workloads.append((PRIMARY,outcome,"quality"))
    failed=0
    for cohort,outcome,scope in workloads:
        print("\nMODEL",cohort,outcome,scope,flush=True)
        try:
            r=fit_one(table,cohort,outcome,scope)
        except (ValueError,RuntimeError,np.linalg.LinAlgError) as exc:
            failed+=1
            print("  MODEL_UNAVAILABLE reason",type(exc).__name__,
                  "no estimates reported")
            continue
        print("  n",r["n"],"aggregated_strata",r["n_strata"],
              "observed_rate_pct","%.2f"%r["observed_pct"],
              "converged",r["converged"])
        for field,ref,level,n_alt,p_ref,p_alt,rd in r["contrasts"]:
            print("  ",field,level,"vs",ref,"n_level",n_alt,
                  "marginal_ref_pct","%.2f"%p_ref,
                  "marginal_level_pct","%.2f"%p_alt,
                  "RD_pp","%+.2f"%rd)
    print("\nSTEP72_MODEL_FAILURES",failed,"of",len(workloads))
    print("NO patient rows exported, NO adjustment for hospital or actual performed imaging.")
    if failed:
        raise ValueError("Step72 exploratory models unavailable; inspect local diagnostics before inference")


def main():
    paths=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    for p in paths:
        if p.is_symlink() or not p.is_file():
            raise FileNotFoundError("Required private Step62/63/68 database missing")
    p62,p63,p68=(p.resolve() for p in paths)
    report=s68.PRIVATE/s68.REPORT
    if report.is_symlink() or not report.is_file():
        raise FileNotFoundError("Step68 frozen aggregate report absent")
    source=json.loads(report.read_text(encoding="utf-8"))
    if source.get("stage")!=s68.POLICY:
        raise ValueError("Step68 scan policy mismatch")
    with sqlite3.connect("file:"+str(p63)+"?mode=ro",uri=True) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:"+str(p62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",
                   ("file:"+str(p68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,p62,p63)
        row=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if row is None:
            raise ValueError("Step68 frozen metadata missing")
        metadata=json.loads(row[0])
        if metadata.get("policy")!=s68.POLICY or (
            metadata.get("s62")!=s68._snapshot(p62)
            or metadata.get("s63")!=s68._snapshot(p63)):
            raise ValueError("Step68 input signature differs")
        table=build(db)
        verify(table,source)
        print_results(table)
    print("\nHANDOFF: TERMINAL OUTPUT ONLY. No zip, private data or model files.")


if __name__=="__main__":
    main()
