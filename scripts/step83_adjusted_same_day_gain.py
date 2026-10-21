#!/usr/bin/env python3
"""Step83: no-rescan, adjusted paired-gain demographic sensitivity.

The gain is an indicator that a CPT14 code is absent on the index
inpatient encounter but present on another same-day encounter.
Only frozen Step62/63/68 indexed-patient/modality flags are read,
inside the approved workstation. No patient-level results are saved.
"""
from __future__ import annotations

from contextlib import closing
import json
import sqlite3
import warnings

import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
    from scripts import step68_joint_imaging_window_scan as s68
    from scripts import step73_uncertainty_support_diagnostics as s73
    from scripts import step82_demographic_definition_sensitivity as s82
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64
    import step68_joint_imaging_window_scan as s68
    import step73_uncertainty_support_diagnostics as s73
    import step82_demographic_definition_sensitivity as s82


SCOPES={
    "quality":((0,1),(0,1)),
    "P0":((0,),(0,1)),
    "P1":((1,),(0,1)),
    "clean":((0,1),(0,)),
}
MIN=11


def gain_table(grouped, frozen):
    """Compute paired newly captured patient counts from nested outcomes."""
    x=grouped.copy()
    for endpoint in s82.OUTCOMES:
        col=endpoint+"_gain"
        x[col]=(x[endpoint+"_day0"]-x[endpoint+"_imp"]).astype(int)
        if (x[col]<0).any() or (x[col]>x.n).any():
            raise ValueError("Non-nested or invalid patient gain")
    base=frozen["patient_cohort_aggregates"]["COHORT|"+s82.PRIMARY]
    if int(x.any_gain.sum())!=int(base["new_day0_other"]):
        raise ValueError("Any-code gain fails frozen Step68 count")
    # Gains by modality are NOT subsets of the any-code gain.
    # A patient may have CT on index IMP and MRI only on another
    # same-day encounter: MRI gain=1 while any-code gain=0.
    return x


def subset(table,scope):
    if scope not in SCOPES:
        raise ValueError("Unsupported P/ambiguity analysis scope")
    ps,hs=SCOPES[scope]
    x=table.loc[table.P.isin(ps)&table.held.isin(hs)].copy()
    if x.empty or int(x.n.sum())<200:
        raise ValueError("Insufficient patient support for restricted model")
    return x


def overlap(x,field,ref,target,scope):
    """Scope-specific overlap, without requiring excluded strata."""
    if field not in ("sex","race","ethnicity"):
        raise ValueError("Unsupported demographic comparison")
    if ref in s82.MISSING or target in s82.MISSING or ref==target:
        return False
    ps,hs=SCOPES[scope]
    # Only requested strata are needed; absent excluded groups are not sparse.
    for p in ps:
        for h in hs:
            for level in (ref,target):
                n=int(x.loc[(x.P==p)&(x.held==h)&(x[field]==level),
                            "n"].sum())
                if n<MIN:
                    return False
    return True


def has_event_complement(x,field,ref,target,event):
    """Keep denominators, events and complements >=11 for both groups."""
    for level in (ref,target):
        subset=x.loc[x[field]==level]
        n=int(subset.n.sum())
        k=int(subset[event].sum())
        if n<2*MIN or k<MIN or n-k<MIN:
            return False
    return True


def model(x,event,scope):
    """Grouped-binomial working model; site clustering unavailable."""
    if event not in [ep+"_gain" for ep in s82.OUTCOMES]:
        raise ValueError("Unsupported gain event")
    x=x.copy()
    x["rate"]=x[event]/x.n
    form="rate ~ C(sex)+C(race)+C(ethnicity)+C(year)+C(age_band)"
    ps,hs=SCOPES[scope]
    if len(ps)==2:
        form+="+P"
    if len(hs)==2:
        form+="+held"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fit=smf.glm(formula=form,data=x,family=sm.families.Binomial(),
                    var_weights=x.n).fit(maxiter=100,disp=False)
    if (not fit.converged
        or not np.isfinite(fit.params.to_numpy()).all()
        or not np.isfinite(fit.cov_params().to_numpy()).all()
        or np.max(np.abs(fit.params.to_numpy()))>24
        or any("PerfectSeparation" in type(w.message).__name__
               for w in caught)):
        raise ValueError("Unstable grouped-binomial model")
    return fit,x


def quality_categories(table):
    """Internal mapping completeness, stratified by source P flag."""
    print("SOURCE DEMOGRAPHIC COMPLETENESS BY P (aggregate shares only)")
    for p in (0,1):
        x=table.loc[table.P==p]
        n=int(x.n.sum())
        for field in ("race","ethnicity"):
            unknown=int(x.loc[x[field]=="UNKNOWN_MISSING","n"].sum())
            unmapped=int(x.loc[x[field].isin(s82.MISSING),"n"].sum())
            if (n<2*MIN or min(unknown,n-unknown,unmapped,n-unmapped)<MIN):
                print("P="+str(p),field,"WITHHELD: small event or complement")
                continue
            print("P="+str(p),field,
                  "unknown_pct","%.2f"%(100*unknown/n),
                  "unknown_plus_unmapped_pct","%.2f"%(100*unmapped/n))
    print("Unknown and other/unmapped are not interchangeable labels.")


def run_summary(grouped,frozen):
    x=gain_table(grouped,frozen)
    print("STEP83 LOCAL ONLY: adjusted demographic sensitivity of ADDED same-day codes")
    print("A gain is paired: code absent on index inpatient, present on another same-day encounter.")
    print("Working-binomial, independent-patient nominal intervals; NO HCO-cluster adjustment.")
    print("Model-adjusted gain contrasts need not equal differences between separately fitted models.")
    print("No clinical-care disparities, performed-scan validation, or site-mechanism inference.")
    print("All subgroup estimates require event/complement and source-quality support.")
    quality_categories(x)
    failed=0
    for scope in SCOPES:
        print("SCOPE",scope)
        part=subset(x,scope)
        for endpoint in s82.OUTCOMES:
            event=endpoint+"_gain"
            try:
                fit,design=model(part,event,scope)
            except (ValueError,RuntimeError,np.linalg.LinAlgError):
                print("GAIN",endpoint,"UNAVAILABLE: model did not pass diagnostics")
                failed+=1
                continue
            for field,ref,target in s82.CONTRASTS:
                label=endpoint+" "+field+" "+target+"_vs_"+ref
                if not overlap(design,field,ref,target,scope):
                    print("GAIN",label,"WITHHELD: sparse applicable P x ambiguity strata")
                    continue
                if not has_event_complement(design,field,ref,target,event):
                    print("GAIN",label,"WITHHELD: small event or complement")
                    continue
                try:
                    t=s73.contrast(fit,design,field,ref,target)
                except (ValueError,RuntimeError,np.linalg.LinAlgError):
                    print("GAIN",label,"UNAVAILABLE: invalid model contrast")
                    failed+=1
                    continue
                print("GAIN",label,"adjusted_difference_in_added_codes_pp",
                      "%+.2f"%t["difference_pp"],
                      "nominal_95CI_pp","[%+.2f,%+.2f]"%
                       (t["nominal_CI_low_pp"],t["nominal_CI_high_pp"]))
    print("STEP83_NUMERIC_MODEL_FAILURES",failed)
    print("Reported intervals are exploratory; independent patients assumed.")
    print("No cross-table public disclosure approval, HCO identifiers or verified acute stroke.")
    print("No source-procedure rescan, private patient export, or external contact.")
    print("HANDOFF: terminal output only; review the scientific decision before document revisions.")


def main():
    paths=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise FileNotFoundError("Frozen Step62/63/68 database missing")
    p62,p63,p68=(p.resolve() for p in paths)
    report=s68.PRIVATE/s68.REPORT
    if report.is_symlink() or not report.is_file():
        raise FileNotFoundError("Frozen Step68 aggregate missing")
    frozen=json.loads(report.read_text(encoding="utf-8"))
    if frozen.get("stage")!=s68.POLICY:
        raise ValueError("Frozen Step68 report policy mismatch")
    with closing(sqlite3.connect("file:"+str(p63)+"?mode=ro",uri=True)) as db:
        db.execute("ATTACH DATABASE ? AS baseline",("file:"+str(p62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",("file:"+str(p68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,p62,p63)
        metadata=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if metadata is None:
            raise ValueError("Missing Step68 input provenance")
        sig=json.loads(metadata[0])
        if (sig.get("policy")!=s68.POLICY or
            sig.get("s62")!=s68._snapshot(p62)
            or sig.get("s63")!=s68._snapshot(p63)):
            raise ValueError("Step68 changed after freezing")
        progress=db.execute(
            "SELECT seen,done FROM capture.progress WHERE stage='procedure'"
        ).fetchone()
        if progress!=(s82.EXPECTED_PROCEDURE_ROWS,1):
            raise ValueError("Original source-scan checkpoint incomplete")
        grouped=s82.group_rows(s82.stream(db))
        s82.verify(grouped,frozen)
    run_summary(grouped,frozen)


if __name__=="__main__":
    main()
