#!/usr/bin/env python3
"""Step79: LOCAL ONLY independent arithmetic and disclosure-risk review of Step78.

Does not rerun patient models or access source SQLite/ZIP. Does not approve
public disclosure, decide care disparity, or modify immutable draft_v1.
Exact source-derived records remain local; terminal prints only statuses.
"""
from __future__ import annotations
import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from PIL import Image

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step78_paper_results_bundle as s78
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step78_paper_results_bundle as s78

IN_DIR=s78.DEST/"draft_v1"
TABLES={
  "t1":"table1_P_and_recording_quality.csv",
  "t2":"table2_P_endpoint_sensitivity.csv",
  "t3":"table3_year_quarantine.csv",
  "t4":"table4_demographic_completeness.csv",
  "t5":"table5_exploratory_demographic_models.csv",
}
FIGURES=(
    "figure1_coded_capture_by_encounter.png",
    "figure2_source_quality_standardization.png",
)
BUNDLE=set(TABLES.values())|set(FIGURES)|{
    "RESULTS_DRAFT_LOCAL_ONLY.md","manifest_LOCAL_ONLY.json",
}
MIN_CELL=11


def check(ok,message):
    if not ok:
        raise ValueError("Step79 integrity failure: "+message)


def integral(s):
    if isinstance(s,bool):
        raise ValueError("Boolean is not a count")
    x=int(s)
    check(str(x)==str(s).strip(),"non-integral count")
    return x


def real(s):
    x=float(s)
    check(math.isfinite(x),"non-finite estimate")
    return x


def near(a,b,name,tol=1e-7):
    check(abs(real(a)-real(b))<=tol,
          "inconsistent "+name)


def read_private_bundle(folder=IN_DIR):
    folder=Path(folder)
    check(folder.is_dir() and not folder.is_symlink(),
          "private draft_v1 directory missing or symlink")
    check(set(p.name for p in folder.iterdir())==BUNDLE,
          "immutable Step78 artifact inventory changed")
    for p in folder.iterdir():
        check(not p.is_symlink() and p.is_file() and p.stat().st_size>0,
              "empty/missing/symlink Step78 artifact")
    tables={}
    for k,name in TABLES.items():
        with (folder/name).open("r",encoding="utf-8",newline="") as handle:
            reader=csv.DictReader(handle)
            check(bool(reader.fieldnames),"missing exhibit header")
            values=list(reader)
        check(len(values)>0,"empty draft exhibit")
        tables[k]=values
    with (folder/"manifest_LOCAL_ONLY.json").open("r",encoding="utf-8") as handle:
        manifest=json.load(handle)
    draft=(folder/"RESULTS_DRAFT_LOCAL_ONLY.md").read_text(encoding="utf-8")
    check(manifest.get("policy")==s78.POLICY,"unrecognized Step78 policy")
    check(manifest.get("primary_cohort")==s78.PRIMARY,
          "wrong primary cohort in draft")
    for k in ("disclosure_review_required","historical_cohort_overlaps_primary",
              "reported_p_is_unvalidated_principal_I63_flag"):
        check(manifest.get(k) is True,k+" not acknowledged")
    for k in ("manuscript_ready_for_public_release",
              "performed_imaging_verified",
              "hospital_cluster_inference_available"):
        check(manifest.get(k) is False,k+" incorrectly marked available")
    for requirement in ("NOT publication- or external-disclosure-ready",
                        "same HCO","scan completion"):
        check(requirement in draft,"missing essential Results limitation")
    check(set(manifest.get("exhibits",[]))==BUNDLE-{"manifest_LOCAL_ONLY.json"},
          "manifest inventory does not match files")
    for name in FIGURES:
        with Image.open(folder/name) as im:
            im.verify()
        with Image.open(folder/name) as im:
            check(im.format=="PNG" and im.width>=800 and im.height>=500,
                  "invalid plot or insufficient draft resolution")
    return tables,manifest,draft


def audit(tables):
    issues=[]
    t1=tables["t1"]; t2=tables["t2"]; t3=tables["t3"]
    t4=tables["t4"]; t5=tables["t5"]
    cohorts=set(s62.COHORTS)
    seen1=set()
    for row in t1:
        k=(row["cohort"],integral(row["P_indicator"]))
        check(k not in seen1 and k[0] in cohorts and k[1] in (0,1),
              "invalid/repeated P cohort in Table1")
        seen1.add(k)
        n=integral(row["denominator"])
        imp=integral(row["index_inpatient_CPT14_n"])
        held=integral(row["any_ambiguous_encounter_patient_n"])
        check(n>=MIN_CELL and 0<=held<=n and 0<=imp<=n,
              "invalid Table1 event/denominator")
        near(row["index_inpatient_CPT14_pct"],100*imp/n,"Table1 capture percent")
        near(row["any_ambiguous_encounter_patient_pct"],
             100*held/n,"Table1 source-quality percent")
    check(seen1==set((c,p) for c in cohorts for p in (0,1)),
          "Table1 cohort/P coverage")
    ref={ (r["cohort"],integral(r["P_indicator"])):r for r in t1 }
    expected=set((c,e[0]) for c in cohorts for e in s78.ENDPOINTS)
    seen2=set()
    for row in t2:
        cohort=row["cohort"]; key=row["endpoint_key"]
        check((cohort,key) in expected and (cohort,key) not in seen2,
              "Table2 incorrect or repeated outcome")
        seen2.add((cohort,key))
        n0=integral(row["P0_n"]); n1=integral(row["P1_n"])
        m0=integral(row["P0_documented_code_n"])
        m1=integral(row["P1_documented_code_n"])
        check(n0==integral(ref[(cohort,0)]["denominator"]) and
              n1==integral(ref[(cohort,1)]["denominator"]),
              "Table1 and Table2 denominators disagree")
        check(0<=m0<=n0 and 0<=m1<=n1,"non-binomial Table2 count")
        p0=100*m0/n0; p1=100*m1/n1
        near(row["P0_crude_pct"],p0,"Table2 P0 percentage")
        near(row["P1_crude_pct"],p1,"Table2 P1 percentage")
        near(row["P1_minus_P0_crude_pp"],p1-p0,"Table2 crude PP")
        near(row["P1_minus_P0_common_year_quarantine_pp"],
             real(row["P1_common_year_quarantine_pct"])-
             real(row["P0_common_year_quarantine_pct"]),
             "Table2 standardization contrast")
        if key=="INDEX_IMP":
            check(m0==integral(ref[(cohort,0)]["index_inpatient_CPT14_n"])
                  and m1==integral(ref[(cohort,1)]["index_inpatient_CPT14_n"]),
                  "frozen inpatient CPT14 baseline disagrees")
        check(row["actual_imaging_performed_verified"]=="False" and
              row["HCO_episode_verified"]=="False",
              "Table2 improperly asserts performed/same-HCO imaging")
    check(seen2==expected,"Table2 outcomes incomplete")
    by={(r["cohort"],r["endpoint_key"]):r for r in t2}
    for cohort in cohorts:
        base=by[cohort,"INDEX_IMP"]
        for p in (0,1):
            a=integral(base["P%d_documented_code_n"%p])
            for outcome in ("INDEX_IMP_OR_SAME_DAY_OTHER",
                            "INDEX_IMP_OR_UNIQUE_ED",
                            "INDEX_IMP_OR_ED_PRE2_DAY0"):
                b=integral(by[cohort,outcome]["P%d_documented_code_n"%p])
                check(a<=b,"alternative outcome does not nest original")
                if 0<b-a<MIN_CELL:
                    issues.append("small_added_code_increment_between_public_tables")
            broad=integral(by[cohort,"INDEX_IMP_OR_ED_PRE2_DAY0"][
                "P%d_documented_code_n"%p])
            same=integral(by[cohort,"INDEX_IMP_OR_SAME_DAY_OTHER"][
                "P%d_documented_code_n"%p])
            ed=integral(by[cohort,"INDEX_IMP_OR_UNIQUE_ED"][
                "P%d_documented_code_n"%p])
            check(broad>=max(same,ed),"broader definition not nested")

    # Source-quality Table3: mutual exclusivity within year and
    # quarantine; percentages alone may reconstruct tiny numerators.
    seen3=set()
    partition=defaultdict(int)
    has_hidden=False
    for row in t3:
        yr=row["year"]; p=integral(row["P_indicator"])
        q=row["any_ambiguous_group"]
        check(yr=="ALL" or yr in tuple(str(y) for y in range(2016,2025)),
              "unknown Table3 year")
        check(q in s78.QUARANTINE_LABELS and p in (0,1),
              "invalid Table3 stratum")
        key=(yr,p,q)
        check(key not in seen3,"duplicate Table3 stratum")
        seen3.add(key)
        hidden=row["cell_suppressed"]=="True"
        if hidden:
            has_hidden=True
            check(row["denominator"] in ("",None) and
                  row["index_inpatient_pct"] in ("",None) and
                  row["index_or_other_day0_pct"] in ("",None),
                  "Table3 suppressed cell has released measures")
        else:
            n=integral(row["denominator"])
            check(n>=MIN_CELL,"Table3 cell below suppression threshold")
            for field in ("index_inpatient_pct","index_or_other_day0_pct"):
                percent=real(row[field])
                check(0<=percent<=100,"invalid Table3 capture rate")
                k=round(n*percent/100)
                if 0<k<MIN_CELL or 0<n-k<MIN_CELL:
                    issues.append("Table3_derived_small_event_or_complement")
            partition[yr,p]+=n
    for p in (0,1):
        n=integral(ref[s78.PRIMARY,p]["denominator"])
        if not has_hidden:
            check(partition["ALL",p]==n and
                  sum(partition[yr,p] for yr in
                      map(str,range(2016,2025)))==n,
                  "Table3 did not partition primary P group")
    if has_hidden:
        issues.append("Table3_suppressed_cells_require_secondary_suppression")

    # Demographics each dimension must partition the full primary cohort,
    # but a withheld category can be inferred from other categories and
    # Table1 totals. This needs manual complementary suppression review.
    seen4=set()
    total=sum(integral(ref[s78.PRIMARY,p]["denominator"]) for p in (0,1))
    for dim in s78.DEMOS:
        subtotal=0
        withheld=0
        for row in t4:
            if row["dimension"]!=dim:
                continue
            cat=(dim,row["category"])
            check(cat not in seen4,"duplicate demographic category")
            seen4.add(cat)
            hidden=row["suppressed"]=="True"
            if hidden:
                withheld+=1
                check(row["n"] in ("",None),"Table4 small category count visible")
                continue
            n=integral(row["n"])
            check(n>=MIN_CELL,"Table4 unsuppressed count under 11")
            subtotal+=n
            near(row["share_pct"],100*n/total,
                 "Table4 category proportion")
            for f in ("P1_pct","index_inpatient_documented_pct",
                      "same_day_encounter_documented_pct"):
                pct=real(row[f]); check(0<=pct<=100,
                                      "Table4 non-binomial percentage")
                numerator=round(pct*n/100)
                if 0<numerator<MIN_CELL or 0<n-numerator<MIN_CELL:
                    issues.append("Table4_derived_small_event_or_complement")
        check(subtotal<=total and
              (withheld or subtotal==total),
              "Table4 demographic partition discrepancy")
        if withheld:
            issues.append("Table4_hidden_category_inferable_from_partition_total")

    check(len(t5)==2*len(s78.s73.TARGETS),
          "Table5 exploratory model inventory incomplete")
    seen5=set()
    for row in t5:
        k=(row["endpoint"],row["dimension"],
           row["reference"],row["comparison"])
        check(k not in seen5 and row["endpoint"] in ("imp_any","same_day_any"),
              "Table5 repeated model contrast")
        seen5.add(k)
        near(row["marginal_difference_pp"],
             real(row["marginal_comparison_pct"])-
             real(row["marginal_reference_pct"]),
             "Table5 marginal contrast")
        d=real(row["marginal_difference_pp"])
        lo=real(row["extra_binomial_sensitivity_low_pp"])
        hi=real(row["extra_binomial_sensitivity_high_pp"])
        check(lo<=d<=hi,"Table5 invalid sensitivity bounds")
        check(row["HCO_cluster_corrected"]=="False" and
              row["case_mix_severity_corrected"]=="False" and
              row["not_confirmed_care_disparity"]=="True",
              "Table5 overstates model validity")
        if integral(row["comparison_n"])<MIN_CELL or integral(
                row["reference_n"])<MIN_CELL:
            issues.append("Table5_suppressed_demographic_model_support")
    # Absence of detected small cells is NOT a full cross-table
    # re-identification or institution-specific release review.
    return sorted(set(issues))


def main():
    tables,manifest,draft=read_private_bundle()
    issues=audit(tables)
    print("STEP79 LOCAL ONLY: manuscript exhibit internal integrity QA")
    print("Step78 manifest, restricted file inventory and 2 PNGs: PASS")
    print("P-group cohort reconciliation, 4 endpoint arithmetic definitions: PASS")
    print("Primary vs expanded CPT14 endpoint containment: PASS")
    print("Provisional model uncertainty and HCO caveats: PASS")
    print("Disclosure risk flags:",len(issues))
    for tag in issues:
        print("  DISCLOSURE_QA_FLAG:",tag)
    print("PUBLIC RELEASE: BLOCKED. Institutional cross-table review required.")
    print("Clinical imaging verification/site adjustment: NOT AVAILABLE.")
    print("No source scans, no mutation of Step78, no new analyses.")
    print("HANDOFF: TERMINAL OUTPUT ONLY; no private tables or images.")


if __name__=="__main__":
    main()
