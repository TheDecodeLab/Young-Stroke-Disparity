#!/usr/bin/env python3
"""Step70: read-only source-quality standardization of P imaging-code contrasts.

Uses ONLY completed local Step62/63/68 SQLite data and Step69's
patient-level aggregate logic. Never prints patient or encounter IDs.
Direct standardization is descriptive QA, NOT an adjusted causal effect.
"""
from __future__ import annotations

from collections import Counter
import json
import sqlite3

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
    from scripts import step68_joint_imaging_window_scan as s68
    from scripts import step69_same_day_attachment_diagnostics as s69
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64
    import step68_joint_imaging_window_scan as s68
    import step69_same_day_attachment_diagnostics as s69

METRICS=(
    ("inpatient_CPT14",("inpatient",)),
    ("inpatient_or_other_same_day_CPT14",("inpatient","new_other_day0")),
    ("inpatient_or_unique_ED_CPT14",("inpatient","new_ed")),
    ("inpatient_or_ED_or_pre2_day0_CPT14",
     ("inpatient","union_ed_or_pre2_day0")),
)
DIMENSIONS={
    "quarantine":"QUARANTINE_P",
    "year":"YEAR_P",
    "year_and_quarantine":"YEAR_QUARANTINE_P",
}


def numerator(c, fields):
    return sum(c[k] for k in fields)


def strata(counts,cohort,kind):
    """Return {(year?, held?): {P: Counter}} from existing patient aggregates.

    Do not parse patient IDs: encoded label contains only cohort/year/P
    and the binary quarantine-status string.
    """
    prefix=DIMENSIONS[kind]
    out={}
    for (group,label),c in counts.items():
        if group!=prefix or not label.startswith(cohort+"|"):
            continue
        trail=label[len(cohort)+1:].split("|")
        if prefix=="QUARANTINE_P":
            p_token,held=trail
            key=(held,)
        elif prefix=="YEAR_P":
            year,p_token=trail
            key=(year,)
        else:
            year,p_token,held=trail
            key=(year,held)
        if p_token not in ("P=0","P=1"):
            raise ValueError("Unexpected P stratum")
        p=int(p_token[-1])
        d=out.setdefault(key,{})
        if p in d:
            raise ValueError("Repeated P stratum")
        d[p]=c
    if not out:
        raise ValueError("No source-quality stratum found: "+kind)
    return out


def standardized(counts,cohort,fields,kind):
    """Common-weight descriptive P-contrast, requiring complete overlap.

    Weight each (year, quarantine) or single-factor stratum by its
    proportion in the original cohort. Same weights apply to both P.
    """
    group=strata(counts,cohort,kind)
    origin=counts[("COHORT",cohort)]["n"]
    weights_n=0
    totals={0:0.0,1:0.0}
    missing=[]
    for key,pmap in sorted(group.items()):
        if any(p not in pmap or pmap[p]["n"]==0 for p in (0,1)):
            missing.append(key)
            continue
        weight=pmap[0]["n"]+pmap[1]["n"]
        weights_n+=weight
        for p in (0,1):
            totals[p]+=weight*numerator(pmap[p],fields)/pmap[p]["n"]
    if missing or weights_n!=origin:
        raise ValueError(
            "Cannot standardize without both P groups in every requested "
            "stratum and full cohort coverage: "+kind+
            ", missing="+str(len(missing))+
            ", covered="+str(weights_n)+", cohort="+str(origin))
    pct={p:100*totals[p]/weights_n for p in (0,1)}
    return pct[0],pct[1],pct[1]-pct[0]


def raw(counts,cohort,fields,held=None):
    if held is None:
        group="P"
        labels=(cohort+"|P=0",cohort+"|P=1")
    else:
        group="QUARANTINE_P"
        labels=(cohort+"|P=0|"+held,cohort+"|P=1|"+held)
    a,b=(counts[(group,label)] for label in labels)
    if not a["n"] or not b["n"]:
        raise ValueError("Cannot compare empty P groups")
    p0=100*numerator(a,fields)/a["n"]
    p1=100*numerator(b,fields)/b["n"]
    return p0,p1,p1-p0


def display(counts):
    print("STEP70 LOCAL-ONLY: descriptive P×quarantine/year CPT14 measurement checks")
    print("Rates are recorded codes, not clinically verified imaging.")
    print("Common-weight standardization is DESCRIPTIVE, not causal adjustment.")
    print("P=0 includes S, blank and otherwise unmarked I63 diagnoses.")
    print("Ambiguous patient status includes ANY quarantined encounter key;")
    print("it does not prove the coded procedure or index itself was incorrect.")
    for cohort in s62.COHORTS:
        print("\nCOHORT",cohort)
        for p in (0,1):
            overall=counts[("P",cohort+"|P="+str(p))]
            held=counts[("QUARANTINE_P",cohort+"|P="+str(p)+"|ANY_AMBIG")]
            print("  P",p,"indexed",overall["n"],
                  "any_ambiguous",held["n"],
                  "ambiguous_pct","%.2f"%(100*held["n"]/overall["n"]))
        for metric,fields in METRICS:
            print("\n  OUTCOME",metric)
            for label,values in (
                ("crude",raw(counts,cohort,fields)),
                ("no_ambiguous",raw(counts,cohort,fields,"NONE")),
                ("any_ambiguous",raw(counts,cohort,fields,"ANY_AMBIG")),
                ("standardized_same_quarantine_mix",
                 standardized(counts,cohort,fields,"quarantine")),
                ("standardized_same_year_mix",
                 standardized(counts,cohort,fields,"year")),
                ("standardized_same_year_and_quarantine_mix",
                 standardized(counts,cohort,fields,"year_and_quarantine"))
            ):
                print("   ",label,
                      "P0_pct","%.2f"%values[0],
                      "P1_pct","%.2f"%values[1],
                      "P1_minus_P0_pp","%+.2f"%values[2])
        print("\n  YEAR × QUARANTINE: same-day expanded CPT14")
        by=strata(counts,cohort,"year_and_quarantine")
        for key,pmap in sorted(by.items()):
            if len(pmap)!=2 or any(pmap[p]["n"]<11 for p in (0,1)):
                print("   ",key,"SUPPRESSED: group n<11")
                continue
            a,b=pmap[0],pmap[1]
            p0=100*(a["inpatient"]+a["new_other_day0"])/a["n"]
            p1=100*(b["inpatient"]+b["new_other_day0"])/b["n"]
            print("   ",key,"n_P0",a["n"],"n_P1",b["n"],
                  "P0_pct","%.2f"%p0,"P1_pct","%.2f"%p1,
                  "P1_minus_P0_pp","%+.2f"%(p1-p0))
    print("\nSTOP: source-quality P groups are NOT demographic disparities.")


def main():
    paths=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError("Expected completed private SQLite missing")
    db62,db63,db68=(p.resolve() for p in paths)
    report=s68.PRIVATE/s68.REPORT
    if report.is_symlink() or not report.is_file():
        raise FileNotFoundError("Step68 local aggregate reference missing")
    reference=json.loads(report.read_text(encoding="utf8"))
    if reference.get("stage")!=s68.POLICY:
        raise ValueError("Step68 report policy mismatch")
    with sqlite3.connect("file:"+str(db63)+"?mode=ro",uri=True) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:"+str(db62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",
                   ("file:"+str(db68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,db62,db63)
        frozen=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if frozen is None:
            raise ValueError("Step68 metadata not frozen")
        meta=json.loads(frozen[0])
        if (meta.get("policy")!=s68.POLICY
                or meta.get("s62")!=s68._snapshot(db62)
                or meta.get("s63")!=s68._snapshot(db63)):
            raise ValueError("Step68 source snapshot changed")
        counts=s69.aggregate(db)
        s69.verify_aggregate(db,counts,reference)
        display(counts)
    print("\nTERMINAL OUTPUT ONLY; no private patient files or ZIP requested.")


if __name__=="__main__":
    main()
