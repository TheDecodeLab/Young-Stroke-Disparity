#!/usr/bin/env python3
"""Step71: LOCAL ONLY, read-only demographic and imaging-outcome feasibility.

This is a descriptive measurement-bias audit, NOT demographic disparities
in clinical receipt of imaging. Reads frozen Step62/63/68 SQLite databases
and never outputs patient or encounter identifiers or raw demographic labels.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
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


ADVANCED=frozenset(("MRI_BRAIN","CTA_HEAD","CTA_NECK","MRA_HEAD","MRA_NECK"))
MODALITIES=frozenset(s62.CPT.values())
FIELDS=("n","P1","held","imp_any","day0_new_any","same_day_any",
        "imp_advanced","day0_new_advanced","same_day_advanced",
        "ed_new_any","CT_HEAD_imp","MRI_BRAIN_imp","CTA_HEAD_imp",
        "CTA_NECK_imp","MRA_HEAD_imp","MRA_NECK_imp")
MISSING=frozenset(("", "UNK", "UNKNOWN", "NULL", "NOT AVAILABLE",
                  "NOT REPORTED", "DECLINED", "PREFER NOT TO ANSWER",
                  "MISSING", "UNSPECIFIED","N/A","UNAVAILABLE"))


def norm(x):
    return " ".join((x or "").replace("_"," ").upper().split())


def category(kind,x):
    """Only predefined broad labels; never echo untrusted source values."""
    val=norm(x)
    if val in MISSING:
        return "UNKNOWN_MISSING"
    mappings={
      "SEX":{
        "MALE":"MALE","M":"MALE","FEMALE":"FEMALE","F":"FEMALE"
      },
      "RACE":{
        "WHITE":"WHITE",
        "BLACK":"BLACK_AFRICAN_AMERICAN",
        "BLACK OR AFRICAN AMERICAN":"BLACK_AFRICAN_AMERICAN",
        "AFRICAN AMERICAN":"BLACK_AFRICAN_AMERICAN",
        "ASIAN":"ASIAN",
        "AMERICAN INDIAN OR ALASKA NATIVE":"AIAN",
        "AMERICAN INDIAN OR ALASKAN NATIVE":"AIAN",
        "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER":"NHPI",
        "TWO OR MORE RACES":"MULTIRACIAL",
        "MULTIPLE RACES":"MULTIRACIAL",
        "OTHER":"OTHER_OR_UNMAPPED",
        "OTHER RACE":"OTHER_OR_UNMAPPED",
      },
      "ETHNICITY":{
        "HISPANIC OR LATINO":"HISPANIC_LATINO",
        "HISPANIC":"HISPANIC_LATINO",
        "LATINO":"HISPANIC_LATINO",
        "NOT HISPANIC OR LATINO":"NOT_HISPANIC_LATINO",
        "NON-HISPANIC":"NOT_HISPANIC_LATINO",
        "NON HISPANIC":"NOT_HISPANIC_LATINO",
        "OTHER":"OTHER_OR_UNMAPPED",
      },
    }
    if kind not in mappings:
        raise ValueError("Unsupported demographic field")
    return mappings[kind].get(val,"OTHER_OR_UNMAPPED")


def measure(modalities, P, held):
    """Derived indicators at one indexed patient/cohort; CPT14 only."""
    bit=0
    advanced=0
    values={}
    for modality,mask in modalities.items():
        if modality not in MODALITIES:
            raise ValueError("Unknown CPT14 modality")
        bit |= int(mask)
        if modality in ADVANCED:
            advanced |= int(mask)
        values[modality+"_imp"]=int(bool(mask & s68.IMP))
    imp=bool(bit & s68.IMP)
    day0=bool(bit & s68.NONIMP_DAY0)
    advanced_imp=bool(advanced & s68.IMP)
    advanced_day0=bool(advanced & s68.NONIMP_DAY0)
    vals=Counter(
        n=1,P1=int(bool(P)),held=int(bool(held)),
        imp_any=int(imp),
        day0_new_any=int(day0 and not imp),
        same_day_any=int(imp or day0),
        imp_advanced=int(advanced_imp),
        day0_new_advanced=int(advanced_day0 and not advanced_imp),
        same_day_advanced=int(advanced_imp or advanced_day0),
        ed_new_any=int(bool(bit & s68.ED) and not imp))
    for m in MODALITIES:
        vals[m+"_imp"]=values.get(m+"_imp",0)
    return vals


def analyze(db):
    """Per-patient stream; no row-level result or free-text label escapes."""
    sql="""
       SELECT i.cohort,i.patient,substr(i.start,1,4) AS year,
              i.principal,p.yob,p.sex,p.race,p.ethnicity,
              CASE WHEN EXISTS(
                SELECT 1 FROM main.ambiguous a
                WHERE a.patient=i.patient) THEN 1 ELSE 0 END AS held,
              f.modality,f.mask
       FROM main.idx i
       LEFT JOIN baseline.person p ON p.patient=i.patient
       LEFT JOIN capture.flags f
         ON f.cohort=i.cohort AND f.patient=i.patient
       ORDER BY i.cohort,i.patient
    """
    counts=defaultdict(Counter)
    current=None
    details=None
    mods={}
    def flush():
        if details is None:
            return
        cohort,year,P,yob,sex,race,ethnicity,held=details
        info=measure(mods,P,held)
        dims={
            "SEX":category("SEX",sex),
            "RACE":category("RACE",race),
            "ETHNICITY":category("ETHNICITY",ethnicity)
        }
        keys=[("COHORT",cohort),
              ("YEAR",cohort+"|"+year),
              ("P",cohort+"|P="+str(P)),
              ("QUARANTINE",cohort+"|"+("ANY_AMBIG" if held else "NONE"))]
        for kind,label in dims.items():
            keys.extend((
                (kind,cohort+"|"+label),
                (kind+"_P",cohort+"|"+label+"|P="+str(P)),
                (kind+"_CLEAN",cohort+"|"+label+"|"+
                    ("ANY_AMBIG" if held else "NONE"))
            ))
        for key in keys:
            counts[key].update(info)
    for cohort,p,year,P,yob,sex,race,ethnicity,held,modality,mask in db.execute(sql):
        key=(cohort,p)
        if key!=current:
            flush()
            current=key
            details=(cohort,year,int(P),yob,sex,race,ethnicity,bool(held))
            mods={}
        if modality is not None:
            if modality in mods:
                raise ValueError("Duplicate patient/cohort/modality")
            mods[modality]=int(mask)
    flush()
    return counts


def verify(db,counts,step68):
    if not counts:
        raise ValueError("Demographic audit has no records")
    for cohort in s62.COHORTS:
        base=counts[("COHORT",cohort)]
        captured=step68["patient_cohort_aggregates"]["COHORT|"+cohort]
        expected={
            "n":int(captured["n"]),
            "imp_any":int(captured["imp"]),
            "day0_new_any":int(captured["new_day0_other"]),
            "ed_new_any":int(captured["new_ed"]),
        }
        for field,n in expected.items():
            if base[field]!=n:
                raise ValueError("Step71 differs from original Step68: "+field)
        for kind in ("SEX","RACE","ETHNICITY","YEAR","P","QUARANTINE"):
            parts=[c for (name,label),c in counts.items()
                   if name==kind and label.startswith(cohort+"|")]
            for f in FIELDS:
                if sum(c[f] for c in parts)!=base[f]:
                    raise AssertionError("Step71 category partition error: "+kind+" "+f)
        for kind in ("SEX","RACE","ETHNICITY"):
            parts=[(key,c) for key,c in counts.items()
                   if key[0]==kind+"_P" and key[1].startswith(cohort+"|")]
            if sum(c["n"] for _,c in parts)!=base["n"]:
                raise AssertionError("P-specific demographic partitions incomplete")
            parts=[(key,c) for key,c in counts.items()
                   if key[0]==kind+"_CLEAN" and key[1].startswith(cohort+"|")]
            if sum(c["n"] for _,c in parts)!=base["n"]:
                raise AssertionError("Quarantine-specific demographic partitions incomplete")
        for f in ("imp_any","imp_advanced","same_day_any","same_day_advanced"):
            if base[f]>base["n"]:
                raise AssertionError("Capture exceeds cohort")
        if not (base["imp_any"]+base["day0_new_any"]==base["same_day_any"]
                and base["imp_advanced"]+base["day0_new_advanced"]==
                    base["same_day_advanced"]):
            raise AssertionError("Invalid capture-union calculation")
    return True


def pct(n,denom):
    return 100*n/denom if denom else 0.0


def display(counts):
    print("STEP71 LOCAL ONLY: demographic coding / imaging-definition FEASIBILITY")
    print("NOT adjusted clinical disparities, radiology-completion, or same-HCO inference.")
    print("Race and ethnicity are separate data fields. No imputation of missing values.")
    print("Other/unmapped pools all values not recognized by a conservative label dictionary.")
    print("Same-day OTHER encounter is NOT a verified stroke care episode.")
    for cohort in s62.COHORTS:
        b=counts[("COHORT",cohort)]
        print("\nCOHORT",cohort,
              "n",b["n"],"inpatient_CPT14",b["imp_any"],
              "same_day_CPT14",b["same_day_any"],
              "inpatient_advanced_CPT14",b["imp_advanced"],
              "same_day_advanced_CPT14",b["same_day_advanced"])
        for kind in ("SEX","RACE","ETHNICITY"):
            print("\n",kind,"(raw category mappings require verification)")
            rows=[(label[len(cohort)+1:],c)
                  for (k,label),c in counts.items()
                  if k==kind and label.startswith(cohort+"|")]
            for label,c in sorted(rows):
                if c["n"]<11:
                    print("  SUPPRESSED category n<11")
                    continue
                n=c["n"]
                print(" ",label,"n",n,
                      "P1_pct","%.1f"%pct(c["P1"],n),
                      "any_ambig_pct","%.1f"%pct(c["held"],n),
                      "IMP_any_pct","%.1f"%pct(c["imp_any"],n),
                      "IMP_adv_pct","%.1f"%pct(c["imp_advanced"],n),
                      "SAME_DAY_any_pct","%.1f"%pct(c["same_day_any"],n),
                      "SAME_DAY_adv_pct","%.1f"%pct(c["same_day_advanced"],n))
            print(" ",kind,"MISSING_OR_UNMAPPED_SHARE",
                  "%.2f"%pct(sum(c["n"] for label,c in rows if label in
                       ("UNKNOWN_MISSING","OTHER_OR_UNMAPPED")),b["n"]))
        if cohort==s62.COHORTS[0]:
            print("\nPRIMARY COHORT: sex/race/ethnicity coding heterogeneity")
            for kind in ("SEX","RACE","ETHNICITY"):
                for subgroup in ("NONE","ANY_AMBIG"):
                    print(" ",kind,subgroup)
                    for (k,label),c in sorted(counts.items()):
                        if k!=kind+"_CLEAN" or not label.startswith(cohort+"|") or (
                                not label.endswith("|"+subgroup)):
                            continue
                        if c["n"]<11:
                            print("   SUPPRESSED category n<11")
                            continue
                        print("  ",label[len(cohort)+1:], "n",c["n"],
                              "P1_pct","%.1f"%pct(c["P1"],c["n"]),
                              "IMP_any_pct","%.1f"%pct(c["imp_any"],c["n"]),
                              "SAME_DAY_any_pct","%.1f"%pct(c["same_day_any"],c["n"]))
    print("\nThese are feasibility checks only. Outcome definition and regression plan remain to be frozen.")


def main():
    inputs=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    for p in inputs:
        if p.is_symlink() or not p.is_file():
            raise FileNotFoundError("Expected private Step62/63/68 databases")
    db62,db63,db68=[p.resolve() for p in inputs]
    report=s68.PRIVATE/s68.REPORT
    if report.is_symlink() or not report.is_file():
        raise FileNotFoundError("Step68 private aggregate reference missing")
    prior=json.loads(report.read_text(encoding="utf8"))
    if prior.get("stage")!=s68.POLICY:
        raise ValueError("Step68 completed policy mismatch")
    with sqlite3.connect("file:"+str(db63)+"?mode=ro",uri=True) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:"+str(db62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",
                   ("file:"+str(db68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,db62,db63)
        frozen=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if not frozen:
            raise ValueError("Missing Step68 input snapshots")
        signature=json.loads(frozen[0])
        if (signature.get("policy")!=s68.POLICY
            or signature.get("s62")!=s68._snapshot(db62)
            or signature.get("s63")!=s68._snapshot(db63)):
            raise ValueError("Step68 snapshot mismatch")
        observed=analyze(db)
        verify(db,observed,prior)
        display(observed)
    print("\nHANDOFF: terminal output ONLY. No raw data or ZIP.")


if __name__=="__main__":
    main()
