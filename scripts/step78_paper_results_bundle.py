#!/usr/bin/env python3
"""Step78: assemble draft manuscript exhibits from FROZEN indexed CPT14 data.

Only the read-only Step62/63/68 SQLite checkpoints are accessed.
Reuses the tested Step69/70 aggregate estimands and Step72/73
grouped demographic models. No original procedure ZIP rescan.
Creates restricted LOCAL ONLY CSV, PNG, MD and manifest artifacts.
Everything is internal/draft until cross-table disclosure and
scientific review; no verified clinical imaging or disparity claim.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
from pathlib import Path
import csv
import hashlib
import json
import os
import sqlite3
import tempfile

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
    from scripts import step68_joint_imaging_window_scan as s68
    from scripts import step69_same_day_attachment_diagnostics as s69
    from scripts import step70_P_quarantine_standardization as s70
    from scripts import step72_exploratory_demographic_models as s72
    from scripts import step73_uncertainty_support_diagnostics as s73
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64
    import step68_joint_imaging_window_scan as s68
    import step69_same_day_attachment_diagnostics as s69
    import step70_P_quarantine_standardization as s70
    import step72_exploratory_demographic_models as s72
    import step73_uncertainty_support_diagnostics as s73

PRIMARY=s62.COHORTS[0]
DEST=s62.ROOT/"results/phase1/full_reconstruction_private/step78_paper_exhibits_private"
POLICY="STEP78_DRAFT_ONLY_RECORDING_ASCERTAINMENT_V1"
MIN_CELL=11
ENDPOINTS=(
    ("INDEX_IMP","Index inpatient CPT14",("inpatient",)),
    ("INDEX_IMP_OR_SAME_DAY_OTHER","Index inpatient or any other same-day encounter CPT14",
     ("inpatient","new_other_day0")),
    ("INDEX_IMP_OR_UNIQUE_ED","Index inpatient or unique preceding ED CPT14",
     ("inpatient","new_ed")),
    ("INDEX_IMP_OR_ED_PRE2_DAY0","Index inpatient or ED/other pre2-day0 CPT14",
     ("inpatient","union_ed_or_pre2_day0")),
)
QUARANTINE_LABELS=("NONE","ANY_AMBIG")
DEMOS=("sex","race","ethnicity")
DISJOINT_CAT={"sex":("UNKNOWN_MISSING",),
              "race":("UNKNOWN_MISSING","OTHER_OR_UNMAPPED"),
              "ethnicity":("UNKNOWN_MISSING","OTHER_OR_UNMAPPED")}


def source_counts(counts):
    """Main patient-level table in mutually exclusive P categories."""
    rows=[]
    for cohort in s62.COHORTS:
        for p in (0,1):
            c=counts[("P",cohort+"|P="+str(p))]
            held=counts[("QUARANTINE_P",
                         cohort+"|P="+str(p)+"|ANY_AMBIG")]
            n=int(c["n"])
            if n<MIN_CELL:
                raise ValueError("Unreportable cohort P cell")
            if held["n"]<0 or held["n"]>n:
                raise ValueError("Invalid quarantine group")
            rows.append({
                "cohort":cohort,"P_indicator":p,"denominator":n,
                "any_ambiguous_encounter_patient_n":int(held["n"]),
                "any_ambiguous_encounter_patient_pct":100*held["n"]/n,
                "index_inpatient_CPT14_n":int(c["inpatient"]),
                "index_inpatient_CPT14_pct":100*c["inpatient"]/n,
                "source_quality_interpretation":
                 "any ambiguous patient key, not necessarily index key",
            })
    return rows


def endpoint_rows(counts):
    """Descriptive primary and historical overlapping-cohort sensitivities.

    Standardized comparison requires common year x patient-level
    encounter-quarantine support, as implemented and verified in Step70.
    """
    rows=[]
    for cohort in s62.COHORTS:
        for key,label,fields in ENDPOINTS:
            p0=counts[("P",cohort+"|P=0")]
            p1=counts[("P",cohort+"|P=1")]
            n0,n1=p0["n"],p1["n"]
            k0,k1=s70.numerator(p0,fields),s70.numerator(p1,fields)
            if any(n<MIN_CELL for n in (n0,n1)):
                raise ValueError("Sparse primary P denominator")
            if any(not 0<=k<=n for k,n in ((k0,n0),(k1,n1))):
                raise ValueError("Nonbinomial documented-code endpoint")
            crude=s70.raw(counts,cohort,fields)
            common=s70.standardized(counts,cohort,fields,"year_and_quarantine")
            only_clean=s70.raw(counts,cohort,fields,"NONE")
            same_year=s70.standardized(counts,cohort,fields,"year")
            rows.append({
                "cohort":cohort,"endpoint_key":key,
                "endpoint_description":label,
                "P0_n":n0,"P1_n":n1,
                "P0_documented_code_n":k0,"P1_documented_code_n":k1,
                "P0_crude_pct":crude[0],"P1_crude_pct":crude[1],
                "P1_minus_P0_crude_pp":crude[2],
                "P0_common_year_quarantine_pct":common[0],
                "P1_common_year_quarantine_pct":common[1],
                "P1_minus_P0_common_year_quarantine_pp":common[2],
                "P1_minus_P0_common_year_only_pp":same_year[2],
                "P1_minus_P0_no_ambiguous_pp":only_clean[2],
                "actual_imaging_performed_verified":False,
                "HCO_episode_verified":False,
            })
    return rows


def quality_rows(counts):
    """Source-quality interaction for the primary cohort, grouped >=11."""
    rows=[]
    for year_scope in ("ALL", "YEAR"):
        years=(None,) if year_scope=="ALL" else tuple(str(y) for y in range(2016,2025))
        for year in years:
            for quarantine in QUARANTINE_LABELS:
                for p in (0,1):
                    if year is None:
                        key=("QUARANTINE_P",
                             PRIMARY+"|P="+str(p)+"|"+quarantine)
                    else:
                        key=("YEAR_QUARANTINE_P",
                             PRIMARY+"|"+year+"|P="+str(p)+"|"+quarantine)
                    c=counts.get(key,Counter())
                    n=int(c["n"])
                    if n==0:
                        continue
                    # For a manuscript table, cells below 11 are
                    # represented only as withheld; never print numerator.
                    row={"year":year or "ALL",
                         "P_indicator":p,"any_ambiguous_group":quarantine,
                         "cell_suppressed":n<MIN_CELL,
                         "denominator":n if n>=MIN_CELL else None,
                         "index_inpatient_pct":
                            100*c["inpatient"]/n if n>=MIN_CELL else None,
                         "index_or_other_day0_pct":
                            100*(c["inpatient"]+c["new_other_day0"])/n
                            if n>=MIN_CELL else None}
                    rows.append(row)
    return rows


def demographic_rows(table):
    """Summary completeness only; descriptive, no disparity inference."""
    x=table.loc[table.cohort==PRIMARY]
    if x.empty:
        raise ValueError("Primary cohort missing")
    total=int(x.n.sum())
    rows=[]
    for name in DEMOS:
        for category,g in x.groupby(name):
            n=int(g.n.sum())
            if n==0:
                continue
            rows.append({
                "dimension":name,"category":str(category),
                "suppressed":n<MIN_CELL,
                "n":n if n>=MIN_CELL else None,
                "share_pct":100*n/total if n>=MIN_CELL else None,
                "P1_pct":100*g.loc[g.P==1,"n"].sum()/n
                         if n>=MIN_CELL else None,
                "index_inpatient_documented_pct":
                   100*g.imp_any.sum()/n if n>=MIN_CELL else None,
                "same_day_encounter_documented_pct":
                   100*g.same_day_any.sum()/n if n>=MIN_CELL else None,
                "missing_or_unmapped":
                  str(category) in DISJOINT_CAT[name],
            })
    return rows


def exploratory_models(table):
    """Two preselected exploratory models. No clinical inference.

    Model conditional nominal CI and overdispersion-widened sensitivity
    DO NOT account for HCO clustering, unmeasured severity or quality.
    """
    rows=[]
    for outcome in ("imp_any","same_day_any"):
        fit,x=s73.fit(table,PRIMARY,outcome,"quality")
        if fit.df_resid<=0:
            raise ValueError("Undefined grouped residual degrees of freedom")
        dispersion=max(1.,float(fit.deviance/fit.df_resid))
        for field,reference,alternative in s73.TARGETS:
            c=s73.contrast(fit,x,field,reference,alternative)
            bound=1.959963984540054*(dispersion**0.5)*c["nominal_SE_pp"]
            rows.append({
                "endpoint":outcome,"model":"exploratory_grouped_glm_quality",
                "dimension":field,"reference":reference,
                "comparison":alternative,"comparison_n":c["n_target"],
                "reference_n":c["n_reference"],
                "marginal_reference_pct":c["reference_pct"],
                "marginal_comparison_pct":c["target_pct"],
                "marginal_difference_pp":c["difference_pp"],
                "nominal_model_95_low_pp":c["nominal_CI_low_pp"],
                "nominal_model_95_high_pp":c["nominal_CI_high_pp"],
                "extra_binomial_sensitivity_low_pp":
                    c["difference_pp"]-bound,
                "extra_binomial_sensitivity_high_pp":
                    c["difference_pp"]+bound,
                "deviance_over_grouped_df":fit.deviance/fit.df_resid,
                "sparse_P_by_ambiguity_support_cells":
                   c["support"]["sparse"],
                "missing_P_by_ambiguity_support_cells":
                   c["support"]["missing"],
                "HCO_cluster_corrected":False,
                "case_mix_severity_corrected":False,
                "not_confirmed_care_disparity":True,
            })
    return rows


def narrative(counts,endpoints,demos,models):
    primary=[x for x in endpoints if x["cohort"]==PRIMARY]
    by={x["endpoint_key"]:x for x in primary}
    b=by["INDEX_IMP"]
    d=by["INDEX_IMP_OR_SAME_DAY_OTHER"]
    y=by["INDEX_IMP_OR_UNIQUE_ED"]
    z=by["INDEX_IMP_OR_ED_PRE2_DAY0"]
    missing={}
    for name in DEMOS:
        xs=[x for x in demos if x["dimension"]==name and x["missing_or_unmapped"]]
        missing[name]=sum(x["n"] or 0 for x in xs)
    txt=f"""# Draft Results for internal investigator review

**Status: NOT publication- or external-disclosure-ready.**
These values are derived from completed private research-network
checkpoints and MUST remain in the restricted local workspace.
P denotes an unvalidated I63 principal coding indicator; P=0
includes secondary/blank/unmarked diagnosis records. Counts are
indexed patients in the uniform ages 18–50 cohort, not two
independent datasets.

## Cohort and recording quality

The frozen uniform 18–50 index-I63 cohort included
{b['P0_n']+b['P1_n']:,} people
(P=0: {b['P0_n']:,}; P=1: {b['P1_n']:,}).
Any-patient-encounter-key ambiguity is NOT necessarily a problem
with the selected index encounter. Demographic missingness and
miscategorization must be evaluated using the internal
table1 and table4 before describing demographic differences.

## Encounter-dependent capture

Documented 14-code CPT neuroimaging was found on the frozen
indexed inpatient encounter in {b['P0_documented_code_n']:,}
P=0 ({b['P0_crude_pct']:.2f}%) and
{b['P1_documented_code_n']:,} P=1
({b['P1_crude_pct']:.2f}%) cohort members.
The unadjusted P1–P0 difference was
{b['P1_minus_P0_crude_pp']:+.2f} percentage points.

Expanding the definition to include codes recorded under a
different encounter on the index admission calendar day
gave P1–P0 difference
{d['P1_minus_P0_crude_pp']:+.2f} pp (unadjusted),
versus {d['P1_minus_P0_common_year_quarantine_pp']:+.2f} pp
when both groups were descriptively standardized to
the same calendar-year × patient-level encounter-key
quarantine distribution. These differing directions
support the sensitivity of code recording to
encounter definition and group/source mix; they do NOT
establish same HCO, same stroke episode or scan completion.

Other prespecified sensitivity comparisons:
unique prior ED linkage, crude
{y['P1_minus_P0_crude_pp']:+.2f} pp and year×quarantine
standardized
{y['P1_minus_P0_common_year_quarantine_pp']:+.2f} pp;
broader ED/pre2/day0, crude
{z['P1_minus_P0_crude_pp']:+.2f} pp and standardized
{z['P1_minus_P0_common_year_quarantine_pp']:+.2f} pp.
The study cannot determine whether code absence
reflects missing care or incomplete recording.

## Exploratory demographic associations

Grouped-binomial analyses of the indexed CPT14 outcome and the
broader other-encounter same-day screen are stored in private
table5, with rates standardized over measured year,
coarsened age-year proxy, demographic labels, P and any
quarantined encounter key. The models are descriptive,
not site-adjusted and not patient-level imaging-care
disparity estimates. Nominal and extra-binomial
uncertainty checks are illustrative ONLY; they
are NOT HCO-cluster robust. Any observed contrasts
must be interpreted alongside unknown/missing
race and ethnicity records and differing
encounter/diagnosis recording.

## What remains before scientific submission

- Internal cross-table disclosure review and approval.
- Independent clinical review of optional exact PCS
  codes and final scope of CPT14 primary/sensitivity
  outcomes. PCS source-row ceilings cannot be
  presented as observed patient gains.
- Methods/limitations review for hospital mix,
  unmeasured stroke severity, uncertain imaging
  performance, overlapping eligibility cohorts,
  demographic missingness and code attribution.
- Confirm that a **measurement-methods paper**
  matches the scientific contribution; do not frame
  these findings as unequal verified clinical care.

**Paper figures and tables:** table1–table5 and
figure1–figure2 are saved alongside this draft.
No manuscript-ready statistical-significance
claims are supported by this package.
"""
    return txt


def write_csv(path,rows):
    if not rows:
        raise ValueError("Refusing empty draft table")
    with path.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plots(table2,folder):
    # Matplotlib imported only in actual local exhibit generation.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    src=[x for x in table2 if x["cohort"]==PRIMARY]
    if len(src)!=len(ENDPOINTS):
        raise ValueError("Missing manuscript primary endpoint scope")
    labels=["Index IMP","IMP + other same-day","IMP + unique ED",
            "IMP + ED/pre2/day0"]
    y0=[x["P0_crude_pct"] for x in src]
    y1=[x["P1_crude_pct"] for x in src]
    idx=list(range(len(labels)))
    f,ax=plt.subplots(figsize=(10,5.5))
    ax.bar([x-.18 for x in idx],y0,width=.36,label="P=0",
           color="#457b9d")
    ax.bar([x+.18 for x in idx],y1,width=.36,label="P=1",
           color="#e09f56")
    ax.set_ylabel("Patients with documented CPT14 codes (%)")
    ax.set_ylim(0,100)
    ax.set_xticks(idx)
    ax.set_xticklabels(labels,rotation=14,ha="right")
    ax.legend(frameon=False)
    for side in ("top","right"):
        ax.spines[side].set_visible(False)
    f.tight_layout()
    f.savefig(folder/"figure1_coded_capture_by_encounter.png",dpi=200)
    plt.close(f)

    crude=[x["P1_minus_P0_crude_pp"] for x in src]
    corrected=[x["P1_minus_P0_common_year_quarantine_pp"] for x in src]
    f,ax=plt.subplots(figsize=(10,5.5))
    ax.axhline(0,color="#555555",lw=1)
    ax.plot(idx,crude,marker="o",lw=2,label="Unstandardized",
            color="#457b9d")
    ax.plot(idx,corrected,marker="s",lw=2,
            label="Same year × source-quality mix",color="#e09f56")
    ax.set_ylabel("P=1 minus P=0 (percentage points)")
    ax.set_xticks(idx)
    ax.set_xticklabels(labels,rotation=14,ha="right")
    ax.legend(frameon=False)
    for side in ("top","right"):
        ax.spines[side].set_visible(False)
    f.tight_layout()
    f.savefig(folder/"figure2_source_quality_standardization.png",dpi=200)
    plt.close(f)


def main():
    inputs=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    if any(path.is_symlink() or not path.is_file() for path in inputs):
        raise FileNotFoundError("Frozen Step62/63/68 databases are required")
    paths=tuple(path.resolve() for path in inputs)
    report=s68.PRIVATE/s68.REPORT
    if report.is_symlink() or not report.is_file():
        raise FileNotFoundError("Step68 baseline aggregate reference missing")
    prior=json.loads(report.read_text(encoding="utf-8"))
    if prior.get("stage")!=s68.POLICY:
        raise ValueError("Unexpected Step68 frozen policy")

    folder=s62._private_dir(DEST)
    outputs=(
        "table1_P_and_recording_quality.csv",
        "table2_P_endpoint_sensitivity.csv",
        "table3_year_quarantine.csv",
        "table4_demographic_completeness.csv",
        "table5_exploratory_demographic_models.csv",
        "figure1_coded_capture_by_encounter.png",
        "figure2_source_quality_standardization.png",
        "RESULTS_DRAFT_LOCAL_ONLY.md",
        "manifest_LOCAL_ONLY.json")
    if any((folder/name).exists() or (folder/name).is_symlink()
           for name in outputs):
        raise FileExistsError("Step78 output already exists; refuse overwrite")
    with closing(sqlite3.connect(
            "file:"+str(paths[1])+"?mode=ro",uri=True)) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:"+str(paths[0])+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",
                   ("file:"+str(paths[2])+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,paths[0],paths[1])
        row=db.execute(
            "SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if row is None:
            raise ValueError("Frozen Step68 signature missing")
        meta=json.loads(row[0])
        if (meta.get("policy")!=s68.POLICY
                or meta.get("s62")!=s68._snapshot(paths[0])
                or meta.get("s63")!=s68._snapshot(paths[1])):
            raise ValueError("Step68 source signatures disagree")
        scan=db.execute(
            "SELECT seen,done FROM capture.progress WHERE stage='procedure'"
        ).fetchone()
        if scan!=(993025015,1):
            raise ValueError("Step68 source procedure scan incomplete")

        source=s69.aggregate(db)
        s69.verify_aggregate(db,source,prior)
        table=s72.build(db)
        s72.verify(table,prior)
        t1=source_counts(source)
        t2=endpoint_rows(source)
        t3=quality_rows(source)
        t4=demographic_rows(table)
        t5=exploratory_models(table)
    if not (len(t1)==len(s62.COHORTS)*2
            and len(t2)==len(s62.COHORTS)*len(ENDPOINTS)
            and len(t5)==2*len(s73.TARGETS)):
        raise ValueError("Unexpected Step78 exhibit dimensions")
    tables=(t1,t2,t3,t4,t5)
    for filename,rows in zip(outputs[:5],tables):
        write_csv(folder/filename,rows)
    plots(t2,folder)
    (folder/outputs[7]).write_text(
        narrative(source,t2,t4,t5),encoding="utf-8")
    receipt={
        "policy":POLICY,
        "source_policy":s68.POLICY,
        "primary_cohort":PRIMARY,
        "historical_cohort_overlaps_primary":True,
        "frozen_sources":{
            "step62":meta["s62"],"step63":meta["s63"],
        },
        "exhibits":list(outputs[:-1]),
        "disclosure_review_required":True,
        "manuscript_ready_for_public_release":False,
        "performed_imaging_verified":False,
        "hospital_cluster_inference_available":False,
        "reported_p_is_unvalidated_principal_I63_flag":True,
        "not_patient_level_exports":True,
    }
    (folder/outputs[-1]).write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n",
        encoding="utf-8")
    print("STEP78 LOCAL ONLY: DRAFT MANUSCRIPT RESULTS EXHIBITS CREATED")
    print("Primary cohort",PRIMARY,
          "P groups",len([r for r in t1 if r["cohort"]==PRIMARY]))
    print("Outcome definitions",len(ENDPOINTS),
          "two overlapping age cohorts")
    print("Draft CSV tables",len(tables),"figures",2,
          "demographic contrasts",len(t5))
    print("Frozen Step68 reference and source signatures: RECONCILED")
    print("Clinically verified scan completion / HCO clustering: NOT AVAILABLE")
    print("Status: INTERNAL RESULTS DRAFT; DISCLOSURE REVIEW REQUIRED")
    print("Private output directory",folder)
    print("HANDOFF: TERMINAL OUTPUT ONLY. Do not upload these results.")


if __name__=="__main__":
    main()
