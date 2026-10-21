#!/usr/bin/env python3
"""Step81: no-rescan feasibility gate for revised young-stroke manuscript.

Answers the two highest-value questions first:
1. How complete are the conservatively mapped race/ethnicity fields?
2. How do six individual CPT14 modalities vary by P and encounter scope?

All source work uses frozen read-only Step62/63/68 SQLite checkpoints.
No treatment flags were preserved at the patient level in these databases.
Numbers are LOCAL ONLY, not approved for publication or external release.
"""
from __future__ import annotations
from collections import Counter
from contextlib import closing
import json
import math
import sqlite3

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
    from scripts import step68_joint_imaging_window_scan as s68
    from scripts import step69_same_day_attachment_diagnostics as s69
    from scripts import step71_demographic_capture_feasibility as s71
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64
    import step68_joint_imaging_window_scan as s68
    import step69_same_day_attachment_diagnostics as s69
    import step71_demographic_capture_feasibility as s71

PRIMARY=s62.COHORTS[0]
MIN_CELL=11
P_LABELS=("P=0","P=1")
WINDOWS=(
    ("index_inpatient","inpatient",()),
    ("plus_other_same_day","inpatient",("new_other_day0",)),
    ("plus_unique_ED","inpatient",("new_ed",)),
    ("plus_pre2_day0","inpatient",("union_ed_or_pre2_day0",)),
)
MODALITIES=tuple(sorted(set(s62.CPT.values())))
UNMAPPED=("UNKNOWN_MISSING","OTHER_OR_UNMAPPED")


def percentage(num,den):
    if not 0<=num<=den or den<=0:
        raise ValueError("Non-binomial patient capture or missing denominator")
    return 100*num/den


def visible(num,den):
    """Preliminary internal non-disclosure guard, not formal approval."""
    return MIN_CELL<=num<=den-MIN_CELL and den>=2*MIN_CELL


def wilson(k,n):
    """Patient-level binomial marginal Wilson interval; ignores site dependence."""
    p=k/n
    z=1.95996398454
    t=z*z/n
    den=1+t
    center=(p+t/2)/den
    half=z*math.sqrt(p*(1-p)/n+t/(4*n*n))/den
    return (100*(center-half),100*(center+half))


def race_feasibility(counts):
    b=counts[("COHORT",PRIMARY)]
    n=int(b["n"])
    if n<=0:
        raise ValueError("Missing primary cohort")
    rows=[]
    for dim in ("RACE","ETHNICITY"):
        unknown=0
        present=0
        total=0
        for (kind,key),value in counts.items():
            if kind!=dim or not key.startswith(PRIMARY+"|"):
                continue
            cat=key[len(PRIMARY)+1:]
            v=int(value["n"])
            total+=v
            if cat in UNMAPPED:
                unknown+=v
            if cat in ("UNKNOWN_MISSING",):
                present+=v
        if total!=n:
            raise ValueError("Category labels do not partition cohort: "+dim)
        rows.append((dim,n,unknown,present))
    return rows


def modality_feasibility(counts):
    """One numerator per patient within each modality and definition."""
    rows=[]
    for modality in MODALITIES:
        for p in (0,1):
            c=counts[("MODALITY_P",PRIMARY+"|P="+str(p)+"|"+modality)]
            n=int(c["n"])
            check=counts[("P",PRIMARY+"|P="+str(p))]
            if n!=int(check["n"]):
                raise ValueError("Modality denominator mismatch with P cohort")
            prev=None
            outcomes={}
            for label,primary,extras in WINDOWS:
                captured=int(c[primary])+sum(int(c[x]) for x in extras)
                if not 0<=captured<=n:
                    raise ValueError("Non-binomial modality numerator")
                if prev is not None and label=="plus_pre2_day0" and captured<prev:
                    # ED-only events must be nested within broader pre2/day0.
                    raise ValueError("Broad modality definition excluded preceding ED")
                outcomes[label]=captured
                if label=="plus_unique_ED":
                    prev=captured
                rows.append((modality,p,label,n,captured))
    return rows


def report(race_rows,modality_rows):
    print("STEP81 LOCAL ONLY: no-rescan demographic coverage and modality capture")
    print("These are DOCUMENTED code flags, not validated imaging completion.")
    for dim,n,unknown,missing in race_rows:
        if visible(unknown,n):
            print(dim,"missing_or_unmapped_pct","%.2f"%percentage(unknown,n))
        else:
            print(dim,"missing_or_unmapped_pct","WITHHELD")
        if visible(missing,n):
            print(dim,"explicit_unknown_pct","%.2f"%percentage(missing,n))
        else:
            print(dim,"explicit_unknown_pct","WITHHELD")
        print(dim,"missingness_interpretation",
              "unmapped and unknown labels are not identical to true missingness")
    print("MODALITY, P, ENCOUNTER_SCOPE, CAPTURE_PCT, WILSON95_PCT")
    print("Wilson intervals are marginal and do NOT account for HCO/site clustering.")
    for modality,p,label,n,k in modality_rows:
        if not visible(k,n):
            print(modality,"P="+str(p),label,"WITHHELD")
            continue
        lo,hi=wilson(k,n)
        print(modality,"P="+str(p),label,"%.2f"%percentage(k,n),
              "%.2f--%.2f"%(lo,hi))
    print("TREATMENT ANCHOR (IV thrombolysis / thrombectomy): NOT available")
    print("Step68 code_profile is aggregate SOURCE ROWS, not patient-level treatment.")
    print("No original source scan; no patient exports; no clinical-care disparity claim.")
    print("HANDOFF: TERMINAL OUTPUT ONLY; local internal disclosure review required.")


def main():
    files=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    if any(f.is_symlink() or not f.is_file() for f in files):
        raise FileNotFoundError("Frozen Step62/63/68 SQLite checkpoints required")
    p62,p63,p68=(f.resolve() for f in files)
    prior_path=s68.PRIVATE/s68.REPORT
    if prior_path.is_symlink() or not prior_path.is_file():
        raise FileNotFoundError("Frozen Step68 report required")
    prior=json.loads(prior_path.read_text(encoding="utf-8"))
    if prior.get("stage")!=s68.POLICY:
        raise ValueError("Unexpected Step68 source policy")
    with closing(sqlite3.connect("file:"+str(p63)+"?mode=ro",uri=True)) as db:
        db.execute("ATTACH DATABASE ? AS baseline",("file:"+str(p62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",("file:"+str(p68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,p62,p63)
        frozen=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if not frozen:
            raise ValueError("Missing Step68 source signature")
        sig=json.loads(frozen[0])
        if (sig.get("policy")!=s68.POLICY or
            sig.get("s62")!=s68._snapshot(p62) or
            sig.get("s63")!=s68._snapshot(p63)):
            raise ValueError("Step68 source signatures disagree")
        quality=s71.analyze(db)
        s71.verify(db,quality,prior)
        groups=s69.aggregate(db)
        s69.verify_aggregate(db,groups,prior)
        r=race_feasibility(quality)
        m=modality_feasibility(groups)
    report(r,m)


if __name__=="__main__":
    main()
