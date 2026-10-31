#!/usr/bin/env python3
"""Step75: correct PCS Imaging-section denominators and audit Step74 candidates.

READ-ONLY on all clinical databases and completed Step74 private report.
Reuses official CMS FY2016-25 ZIPs already downloaded for Step74;
no source ZIP scan, no network, no personal identifiers printed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path
import hashlib
import json
import re
import sqlite3

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
    from scripts import step68_joint_imaging_window_scan as s68
    from scripts import step74_cms_pcs_codebook_review as s74
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64
    import step68_joint_imaging_window_scan as s68
    import step74_cms_pcs_codebook_review as s74

VALID_PCS=re.compile(r"^[0-9A-HJ-NP-Z]{7}$")
CLASSES=(
    "all_PCS_rows",
    "non_B_rows",
    "B_rows",
    "B_valid_shape",
    "B_bad_shape",
    "B_matched_neighbor_FY",
    "B_unmatched_neighbor_FY",
    "B_matched_review_only",
)
TAG2PREFIX={
    "REVIEW_CNS_CT":"B02","REVIEW_CNS_MR":"B03",
    "REVIEW_UPPER_ARTERIAL_CT":"B32","REVIEW_UPPER_ARTERIAL_MR":"B33",
}


def load_cached():
    """Validate cache identities against completed Step74 metadata receipts."""
    path=s74.PRIVATE/s74.REPORT
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError("Step74 LOCAL ONLY report does not exist")
    report=json.loads(path.read_text(encoding="utf8"))
    if report.get("policy")!="STEP74_DISCOVERY_ONLY_V1":
        raise ValueError("Wrong Step74 discovery policy")
    meta=report.get("official_catalog_fy_metadata",{})
    titles={}
    for year in s74.FY:
        saved=s74.PRIVATE/("cms_pcs_FY"+str(year)+".zip")
        if saved.is_symlink() or not saved.is_file():
            raise FileNotFoundError("Official CMS FY ZIP missing from cached Step74 data")
        binary=saved.read_bytes()
        signature=hashlib.sha256(binary).hexdigest()
        if signature!=meta[str(year)]["sha256"]:
            raise ValueError("CMS public ZIP digest changed since Step74")
        parsed=s74.parse_titles(binary)
        if len(parsed)!=meta[str(year)]["section_B_code_titles"]:
            raise ValueError("Step74 CMS B-section title count changed")
        titles[year]=parsed
    return titles,report


def audit_rows(source, cms):
    """Audit source-row counts at overlapping-cohort membership grain.

    'valid_shape' concerns only the ICD-10-PCS seven-character syntax,
    not whether the code actually appears in official CMS catalogs.
    """
    output=defaultdict(Counter)
    reasons=defaultdict(Counter)
    for code,scope,year,P,n in source:
        if scope not in s74.SCOPES or not 2016<=int(year)<=2024:
            continue
        if int(P) not in (0,1) or int(n)<0:
            raise ValueError("Malformed Step68 source-code profile")
        k=(int(year),int(P),scope)
        n=int(n)
        c=output[k]
        c["all_PCS_rows"]+=n
        if not code.startswith("B"):
            c["non_B_rows"]+=n
            continue
        c["B_rows"]+=n
        if not VALID_PCS.fullmatch(code):
            c["B_bad_shape"]+=n
            reasons[(scope,"BAD_SHAPE")][code[:3]]+=n
            continue
        c["B_valid_shape"]+=n
        titles=[cms[fiscal][code] for fiscal in (int(year),int(year)+1)
                if code in cms.get(fiscal,{})]
        if not titles:
            c["B_unmatched_neighbor_FY"]+=n
            reasons[(scope,"NOT_IN_NEIGHBOR_FY")][code[:3]]+=n
            continue
        c["B_matched_neighbor_FY"]+=n
        tags=set(filter(None,(s74.candidate(code,t) for t in titles)))
        if tags:
            c["B_matched_review_only"]+=n
            for tag in tags:
                c[tag+"_rows"]+=n
        else:
            c["B_matched_not_candidate"]+=n
    return output,reasons


def verify(source, step74, counts):
    """Independent crosswalk reconciliation to Step74 source-row report."""
    old=step74["source_row_aggregates_LOCAL_ONLY"]
    expected_keys=set()
    for (year,P,scope),c in counts.items():
        key="|".join((str(year),str(P),scope))
        expected_keys.add(key)
        if key not in old:
            raise ValueError("Step74 source-row report missing scope/year/P: "+key)
        previous=old[key]
        if c["all_PCS_rows"]!=int(previous["source_rows"]):
            raise ValueError("Step74 all-PCS row count does not reconcile")
        if c["B_matched_neighbor_FY"]!=int(
                previous.get("in_at_least_one_neighbor_FY_rows",0)):
            raise ValueError("Step74 CMS match count does not reconcile")
        if c["B_matched_review_only"]!=int(
                previous.get("REVIEW_ONLY_potential_neuroimaging_source_rows",0)):
            raise ValueError("Step74 review candidate count does not reconcile")
        if (c["B_rows"]+c["non_B_rows"]!=c["all_PCS_rows"] or
            c["B_bad_shape"]+c["B_valid_shape"]!=c["B_rows"] or
            c["B_matched_neighbor_FY"]+
             c["B_unmatched_neighbor_FY"]!=c["B_valid_shape"] or
            c["B_matched_review_only"]>c["B_matched_neighbor_FY"]):
            raise AssertionError("ICD-10-PCS imaging section partition failed")
    if expected_keys!=set(old):
        raise ValueError("Step74 source-row report keys disagree with Step75")
    return True


def safe(n):
    return str(n) if n>=11 else ("<11" if n else "0")


def show(counts,reasons,catalog):
    # The real Step74 cache is a complete FY2016-2025 catalog. Detect
    # incomplete fixtures or metadata before printing a partial report.
    missing=sorted(set(s74.FY)-set(catalog))
    if missing:
        raise ValueError("Step75 CMS FY catalog incomplete: "+
                         ",".join(str(y) for y in missing))
    totals=defaultdict(Counter)
    for (year,P,scope),c in counts.items():
        totals[("ALL",scope)].update(c)
        totals[("P",str(P),scope)].update(c)
        totals[("YEAR",str(year),scope)].update(c)
    print("STEP75 LOCAL ONLY: correct section-B denominator for Step74 CMS crosswalk")
    print("Units = source procedure rows multiplied by overlapping cohort memberships.")
    print("All PCS includes NON-IMAGING sections; CMS title catalog contains B only.")
    print("B-prefix codes are imaging-section codes, NOT automatically brain imaging.")
    print("CMS FY matching is year-adjacent SCREEN only, not exact discharge-date validity.")
    for group in ("ALL","P","YEAR"):
        print("\nSTRATUM",group)
        for k,v in sorted(totals.items()):
            if k[0]!=group or v["all_PCS_rows"]<11:
                continue
            total=v["all_PCS_rows"];b=v["B_rows"]
            match=v["B_matched_neighbor_FY"]
            print("|".join(k),
                  "all_PCS",total,
                  "non_B",safe(v["non_B_rows"]),
                  "B_section",safe(b),
                  "B_percent_of_all_PCS","%.2f"%(100*b/total),
                  "B_well_formed",safe(v["B_valid_shape"]),
                  "B_bad_shape",safe(v["B_bad_shape"]),
                  "B_CMS_matched",safe(match),
                  "B_CMS_match_pct","%.2f"%(100*match/b) if b else "NA",
                  "B_CMS_unmatched",safe(v["B_unmatched_neighbor_FY"]),
                  "review_only_source_rows",safe(v["B_matched_review_only"]))
            if group=="ALL":
                for tag in TAG2PREFIX:
                    print("  "+tag,safe(v[tag+"_rows"]))
    print("\nUNMATCHED B-SECTION CODE PREFIXES (not exact codes; source rows)")
    for (scope,reason),freq in sorted(reasons.items()):
        vals=sorted(freq.items(),key=lambda kv:(-kv[1],kv[0]))
        print(scope,reason,"top_prefixes",
              " ".join(prefix+":"+safe(n) for prefix,n in vals[:10]))
    print("\nOFFICIAL PUBLIC CMS CATALOG PROVENANCE")
    for yr in s74.FY:
        print("FY",yr,"B_section_code_titles",len(catalog[yr]))
    print("\nNo patient-level imaging gain can be inferred from source-row counts.")
    print("No original procedure-source re-read was performed.")


def main():
    paths=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise FileNotFoundError("Frozen clinical checkpoints absent")
    db62,db63,db68=(p.resolve() for p in paths)
    report_path=s68.PRIVATE/s68.REPORT
    if report_path.is_symlink() or not report_path.is_file():
        raise FileNotFoundError("Completed Step68 aggregate reference absent")
    previous=json.loads(report_path.read_text(encoding="utf8"))
    if previous.get("stage")!=s68.POLICY:
        raise ValueError("Step68 aggregate policy mismatch")
    titles,step74=load_cached()
    with closing(sqlite3.connect("file:"+str(db63)+"?mode=ro",uri=True)) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:"+str(db62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",
                   ("file:"+str(db68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,db62,db63)
        source_meta=db.execute(
            "SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if not source_meta:
            raise ValueError("Frozen Step68 source signature absent")
        signature=json.loads(source_meta[0])
        if (signature.get("policy")!=s68.POLICY or
            signature.get("s62")!=s68._snapshot(db62) or
            signature.get("s63")!=s68._snapshot(db63)):
            raise ValueError("Step68 private snapshot changed")
        progress=db.execute(
            "SELECT seen,done FROM capture.progress WHERE stage='procedure'").fetchone()
        if progress!=(993025015,1):
            raise ValueError("Step68 checkpoint not fully scanned")
        source=db.execute("""
          SELECT code,scope,service_year,P,SUM(n)
          FROM capture.code_profile
          WHERE system='ICD-10-PCS'
          GROUP BY code,scope,service_year,P
        """)
        counts,reasons=audit_rows(source,titles)
        verify(source,step74,counts)
        show(counts,reasons,titles)
    print("\nHANDOFF: TERMINAL OUTPUT ONLY. No ZIP or private results file.")


if __name__=="__main__":
    main()
