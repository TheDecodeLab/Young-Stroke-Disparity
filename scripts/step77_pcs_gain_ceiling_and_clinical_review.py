#!/usr/bin/env python3
"""Step77: conservative PCS patient-gain ceiling + local clinical review sheet.

NO source table scan, NO new regression. Reads completed Step68, Step74,
Step76 private aggregate JSON only. Does not add PCS to patient endpoints.
The private exact-code review CSV is not a shareable public codebook.
"""
from __future__ import annotations

import csv
import json
from collections import Counter,defaultdict
from pathlib import Path
import os
import tempfile

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step68_joint_imaging_window_scan as s68
    from scripts import step74_cms_pcs_codebook_review as s74
    from scripts import step76_exact_PCS_anatomy_review as s76
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step68_joint_imaging_window_scan as s68
    import step74_cms_pcs_codebook_review as s74
    import step76_exact_PCS_anatomy_review as s76

OUT=s62.ROOT/"results/phase1/full_reconstruction_private/step77_decision_gate_private"
CSV_NAME="step77_clinical_code_review_LOCAL_ONLY.csv"
FAMILY={
    "B02":"CNS_CT",
    "B03":"CNS_MR",
    "B32":"UPPER_ARTERY_CT",
    "B33":"UPPER_ARTERY_MR",
}
CSV_FIELDS=(
    "code","candidate_family","official_CMS_titles_across_neighbor_years",
    "source_service_years","review_anatomy_and_method",
    "review_contrast_if_verifiable",
    "review_include_or_exclude","reviewer_rationale",
    "reviewer_name_or_initials","review_date",
    "FY_discharge_date_validity_checked",
    "source_coverage_note"
)


def load_private(path, policy_key, expected):
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError("Required private aggregate evidence absent: "+path.name)
    report=json.loads(path.read_text(encoding="utf-8"))
    if report.get(policy_key)!=expected:
        raise ValueError("Wrong frozen evidence policy: "+path.name)
    return report


def analysis(reference,profiles,queue_doc,cohort):
    """Derive an upper bound, never estimate an actual expanded outcome.

    The source PCS rows are summed across TWO overlapping cohorts. Thus
    all source candidate rows at P=1 form a deliberately over-generous
    ceiling for the maximum number of P=1 patients newly CPT-positive
    in the subset that is the primary uniform 18-50 cohort.
    """
    prior=reference["patient_cohort_aggregates"]
    by_p=[]
    for p in (0,1):
        key="P|"+cohort+"|P="+str(p)
        if key not in prior:
            raise ValueError("Frozen Step68 report missing primary P stratum")
        group=prior[key]
        n=int(group["n"])
        imp=int(group["imp"])
        if n<1 or not 0<=imp<=n:
            raise ValueError("Invalid frozen primary CPT14 denominator")
        by_p.append((n,imp))

    rows=profiles["source_row_aggregates_LOCAL_ONLY"]
    per=defaultdict(Counter)
    for key,record in rows.items():
        year,P,scope=key.split("|")
        if not (2016<=int(year)<=2024 and P in ("0","1")
                and scope in s74.SCOPES):
            raise ValueError("Unexpected Step74 year/P/scope key")
        count=int(record["REVIEW_ONLY_potential_neuroimaging_source_rows"])
        if count<0:
            raise ValueError("Negative Step74 PCS candidate source rows")
        per[P][scope]+=count
    if any(scope not in per[str(p)] for p in (0,1) for scope in ("INDEX_IMP",)):
        raise ValueError("Missing P-specific inpatient source profile")
    by_scope=Counter()
    for k,v in per.items():
        by_scope.update(v)
    if sum(by_scope.values())!=sum(
        int(x["observed_source_rows_cohort_memberships"])
        for x in queue_doc["review_queue_LOCAL_ONLY"]):
        raise ValueError("Step76 review inventory and Step74 source candidates disagree")

    for item in queue_doc["review_queue_LOCAL_ONLY"]:
        if (item["clinical_reviewer_approval"]!="PENDING" or
                item["exact_discharge_date_validity"]!="NOT_ASSESSED"):
            raise ValueError("Unexpected source review state; adjudication required")
        if item["family"] not in FAMILY or (
                item["modality_candidate"]!=FAMILY[item["family"]]):
            raise ValueError("Mismatched candidate code family")
    for p in (0,1):
        if by_p[p][0]-by_p[p][1]<0:
            raise ValueError("Negative CPT14-negative count")

    results=[]
    for p in (0,1):
        n,imp=by_p[p]
        total_rows=per[str(p)]["INDEX_IMP"]
        absolute_extra=min(n-imp,total_rows)
        # This is a mathematical ceiling assuming every source row
        # represents a distinct new patient in this particular cohort.
        # It ignores duplicated rows and prior CPT14 overlap by design.
        results.append({
            "P":p,"n":n,"inpatient_CPT14_patients":imp,
            "CPT14_pct":100*imp/n,
            "PCS_index_candidate_source_rows_BOTH_overlapping_cohorts":total_rows,
            "MAX_new_patients_PCS_INDEX_only_unrealistic":absolute_extra,
            "MAX_index_CPT14_or_PCS_candidate_pct_UNREALISTIC":
                100*(imp+absolute_extra)/n,
            "MAX_increment_pp_UNREALISTIC":100*absolute_extra/n,
        })
    p0,p1=results
    minimal_gap_pp=p0["CPT14_pct"]-p1[
        "MAX_index_CPT14_or_PCS_candidate_pct_UNREALISTIC"]
    return results,by_scope,minimal_gap_pp


def review_rows(doc):
    queue=doc["review_queue_LOCAL_ONLY"]
    if len(queue)==0:
        raise ValueError("No PCS candidates for clinical code review")
    if len({q["code"] for q in queue})!=len(queue):
        raise ValueError("Repeated exact PCS candidate code")
    data=[]
    for q in sorted(queue,key=lambda r:r["code"]):
        code=q["code"]
        if len(code)!=7 or q["family"]!=code[:3]:
            raise ValueError("Malformed candidate exact code")
        title=" || ".join(q["FY_titles_for_review"])
        # Do NOT silently convert a rule-based candidate to a clinical approval.
        # Not all CMS official titles include enough information to classify
        # contrast/method or exact date validity.
        data.append({
            "code":code,
            "candidate_family":q["modality_candidate"],
            "official_CMS_titles_across_neighbor_years":title,
            "source_service_years":",".join(map(str,q["observed_source_service_years"])),
            "review_anatomy_and_method":"PENDING",
            "review_contrast_if_verifiable":"PENDING",
            "review_include_or_exclude":"PENDING",
            "reviewer_rationale":"",
            "reviewer_name_or_initials":"",
            "review_date":"",
            "FY_discharge_date_validity_checked":"NO",
            "source_coverage_note":"OBSERVED_IN_SOURCE_PRIVATE; NOT_PATIENT_LEVEL",
        })
    return data


def save_review_csv(path,records):
    """Atomic, non-overwriting, private-only review worksheet."""
    if path.exists() or path.is_symlink():
        raise FileExistsError("Existing Step77 review sheet cannot be overwritten")
    if not records:
        raise ValueError("Refusing empty clinical review sheet")
    fd,tmp=tempfile.mkstemp(prefix=".step77_",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",newline="",encoding="utf-8") as fh:
            writer=csv.DictWriter(fh,fieldnames=CSV_FIELDS,
                                  extrasaction="raise")
            writer.writeheader()
            writer.writerows(records)
        os.chmod(tmp,0o600)
        os.link(tmp,path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def print_summary(stats,by_scope,min_gap,cohort,ncodes):
    print("STEP77 LOCAL ONLY: PCS codebook clinical-review / maximum-capture decision")
    print("This is a *mathematical upper bound*, NOT an expanded patient outcome.")
    print("PCS source rows were counted across two overlapping age cohorts.")
    print("A source row can duplicate a patient or an existing CPT14 code.")
    print("Assume implausibly that every indexed PCS candidate row is a")
    print("different previously CPT14-negative member of the uniform cohort.")
    print("PRIMARY_COHORT",cohort)
    for row in stats:
        print("P",row["P"],"cohort_n",row["n"],
              "baseline_CPT14_patients",row["inpatient_CPT14_patients"],
              "baseline_pct","%.2f"%row["CPT14_pct"],
              "index_PCS_candidate_rows_ACROSS_BOTH_COHORTS",
                  row["PCS_index_candidate_source_rows_BOTH_overlapping_cohorts"],
              "MAX_PCS_possible_gain_patients",
                  row["MAX_new_patients_PCS_INDEX_only_unrealistic"],
              "MAX_CPT14_plus_PCS_pct_UNREALISTIC",
                  "%.2f"%row["MAX_index_CPT14_or_PCS_candidate_pct_UNREALISTIC"])
    print("MIN_P0_vs_P1_index_code_capture_gap_pp_EVEN_UNDER_MAX_P1_GROWTH",
          "%+.2f"%min_gap)
    print("Candidate source-row totals by encounter scope:")
    for scope in s74.SCOPES:
        print(" ",scope,by_scope[scope])
    print("Exact observed code review queue length",ncodes)
    print("Critical: all Step76 anatomy-positive codes were PRESELECTED")
    print("by anatomy keywords in Step74; this is NOT independent validation.")
    print("No scan, no new patient classifications, no causal disparity claim.")


def main():
    reference=load_private(s68.PRIVATE/s68.REPORT,"stage",s68.POLICY)
    profiles=load_private(s74.PRIVATE/s74.REPORT,"policy",
                          "STEP74_DISCOVERY_ONLY_V1")
    inventory=load_private(s76.PRIVATE/s76.REPORT,"policy",
                           "STEP76_CODEBOOK_DISCOVERY_ONLY_V1")
    stats,by_scope,min_gap=analysis(
        reference,profiles,inventory,s62.COHORTS[0])
    records=review_rows(inventory)
    print_summary(stats,by_scope,min_gap,s62.COHORTS[0],len(records))
    folder=s62._private_dir(OUT)
    target=folder/CSV_NAME
    save_review_csv(target,records)
    print("LOCAL_ONLY exact-code clinician worksheet:",target)
    print("No private files or source ZIP requested; return TERMINAL OUTPUT ONLY.")


if __name__=="__main__":
    main()
