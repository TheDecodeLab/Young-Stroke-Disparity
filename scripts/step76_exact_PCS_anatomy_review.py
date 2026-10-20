#!/usr/bin/env python3
"""Step76: local-only exact PCS candidate anatomy and time-pattern review.

Reads completed Step74 JSON and CMS FY2016-25 public ZIP cache. No
TriNetX source-table scan, patient flags, or clinical records processed.
Exact code + source-frequency records are written PRIVATE ONLY.
Output is a candidate review queue, NOT an approved imaging codebook.
"""
from __future__ import annotations

from collections import Counter,defaultdict
import json
import os
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step74_cms_pcs_codebook_review as s74
    from scripts import step75_pcs_section_denominator_audit as s75
    from scripts import step68_joint_imaging_window_scan as s68
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step74_cms_pcs_codebook_review as s74
    import step75_pcs_section_denominator_audit as s75
    import step68_joint_imaging_window_scan as s68

PRIVATE=s62.ROOT/"results/phase1/full_reconstruction_private/step76_code_review_private"
REPORT="step76_exact_PCS_review_queue_LOCAL_ONLY.json"
GROUPS={"2016-2018":range(2016,2019),
        "2019-2021":range(2019,2022),
        "2022-2024":range(2022,2025)}
MODALITY={
 "B02":"CNS_CT",
 "B03":"CNS_MR",
 "B32":"UPPER_ARTERY_CT",
 "B33":"UPPER_ARTERY_MR",
}
BRAIN=("brain","cerebr","intracranial","head")
VESSELS=("carotid","vertebral arter","intracranial arter",
         "cervico-cerebral","cervicocerebral")


def judgment(code,titles):
    """Anatomy screening ONLY; final decision requires human review.

    Official full descriptions are checked as a family across the
    two neighboring CMS fiscal years; a changing title requires
    separate review, and no anatomy is assumed from B-prefix alone.
    """
    if code[:3] not in MODALITY or len(code)!=7 or not titles:
        raise ValueError("Candidate does not have a reviewed PCS family/title")
    lower=[" ".join(str(t).lower().split()) for t in titles]
    family=code[:3]
    if family in ("B02","B03"):
        if all(any(t in title for t in BRAIN) for title in lower):
            return "BRAIN_ANATOMY_CANDIDATE"
        return "ANATOMY_UNRESOLVED"
    if all(any(t in title for t in VESSELS) for title in lower):
        return "HEAD_NECK_VESSEL_CANDIDATE"
    return "ANATOMY_UNRESOLVED"


def assess(step74,official):
    """Returns mutually reconciling group counters + private queue."""
    if step74.get("policy")!="STEP74_DISCOVERY_ONLY_V1":
        raise ValueError("Unrecognized Step74 evidence policy")
    details=step74.get(
        "public_codes_plus_private_source_frequencies_LOCAL_ONLY",[])
    published=step74.get("source_row_aggregates_LOCAL_ONLY",{})
    evidence=defaultdict(Counter)
    codes=defaultdict(lambda:{"rows":0,"years":set(),"scopes":set(),
                              "P":set(),"FY_titles":set(),
                              "statuses":set()})
    seen=set()
    for rec in details:
        year=int(rec["service_year"])
        P=int(rec["P"])
        scope=rec["scope"]
        code=rec["code"]
        count=int(rec["source_rows_cohort_memberships"])
        if (year not in range(2016,2025) or P not in (0,1)
                or scope not in s74.SCOPES or
                code[:3] not in MODALITY or count<0):
            raise ValueError("Unexpected Step74 exact-code evidence")
        key=(year,P,scope,code)
        if key in seen:
            raise ValueError("Duplicate Step74 code-frequency cell")
        seen.add(key)
        official_titles=tuple(
            official[fy][code] for fy in (year,year+1)
            if code in official[fy])
        if not official_titles:
            raise ValueError("Step74 candidate absent from CMS neighbor years")
        if sorted(official_titles)!=sorted(rec["FY_titles"]):
            raise ValueError("Cached official CMS title changed since Step74")
        status=judgment(code,official_titles)
        mode=MODALITY[code[:3]]
        signature=(str(year),str(P),scope)
        evidence[("STRATUM",)+signature]["candidate_rows"]+=count
        evidence[("STRATUM",)+signature][status+"_rows"]+=count
        evidence[("MODE",mode)]["candidate_rows"]+=count
        evidence[("MODE_YEAR",mode,str(year))]["candidate_rows"]+=count
        evidence[("MODE",mode)][status+"_rows"]+=count
        evidence[("YEAR",str(year))]["candidate_rows"]+=count
        evidence[("YEAR",str(year))][status+"_rows"]+=count
        evidence[("P",str(P))]["candidate_rows"]+=count
        evidence[("P",str(P))][status+"_rows"]+=count
        evidence[("SCOPE",scope)]["candidate_rows"]+=count
        evidence[("SCOPE",scope)][status+"_rows"]+=count
        key_entry=codes[code]
        key_entry["rows"]+=count
        key_entry["years"].add(year)
        key_entry["scopes"].add(scope)
        key_entry["P"].add(P)
        key_entry["FY_titles"].update(official_titles)
        key_entry["statuses"].add(status)

    # Independently reconcile the exact-code candidate sum to the
    # published Step74 year/P/scope source-row aggregates.
    all_cells=0
    for label,rec in published.items():
        yy,pp,scope=label.split("|")
        key=("STRATUM",yy,pp,scope)
        expected=int(rec.get(
            "REVIEW_ONLY_potential_neuroimaging_source_rows",0))
        observed=evidence[key]["candidate_rows"]
        if expected!=observed:
            raise ValueError("Step76 candidate source rows differ from Step74: "+label)
        all_cells+=expected
    if all_cells!=sum(x["rows"] for x in codes.values()):
        raise ValueError("Step76 source row total fails exact-code reconciliation")

    if not codes:
        raise ValueError("Empty Step74 candidate code inventory")
    review=[]
    for code,item in sorted(codes.items()):
        statuses=sorted(item["statuses"])
        review.append({
            "code":code,
            "family":code[:3],
            "modality_candidate":MODALITY[code[:3]],
            "anatomy_review_status":statuses[0] if len(statuses)==1
                                      else "INCONSISTENT_FY_ANATOMY_REVIEW",
            "FY_titles_for_review":sorted(item["FY_titles"]),
            "observed_source_service_years":sorted(item["years"]),
            "observed_scopes":sorted(item["scopes"]),
            "observed_P_categories":sorted(item["P"]),
            "observed_source_rows_cohort_memberships":item["rows"],
            "NOT_patient_count":True,
            "clinical_reviewer_approval":"PENDING",
            "exact_discharge_date_validity":"NOT_ASSESSED",
        })
    return evidence,review


def b_source_counts(dbfile,step74):
    """Reuse indexed source code-frequency profile, NOT the clinical ZIP.

    Independently reconcile all-PCS row counts by date/P/scope before
    interpreting imaging B-section rates from this same profile.
    """
    if dbfile.is_symlink() or not dbfile.is_file():
        raise FileNotFoundError("Completed Step68 code profile SQLite missing")
    all_rows=Counter()
    b_rows=Counter()
    with closing(sqlite3.connect("file:"+str(dbfile.resolve())+"?mode=ro",
                                 uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        for yr,P,scope,code,n in db.execute("""
            SELECT service_year,P,scope,code,n FROM code_profile
            WHERE system='ICD-10-PCS'
        """):
            if scope not in s74.SCOPES or not 2016<=int(yr)<=2024:
                continue
            key=(str(yr),str(P),scope)
            all_rows[key]+=int(n)
            if code.startswith("B"):
                b_rows[key]+=int(n)
    published=step74.get("source_row_aggregates_LOCAL_ONLY",{})
    if set("|".join(k) for k in all_rows)!=set(published):
        raise ValueError("Step76 PCS year/P/scope keys do not reconcile to Step74")
    for key,n in all_rows.items():
        if n!=int(published["|".join(key)]["source_rows"]):
            raise ValueError("Step76 PCS source counts changed since Step74")
    return b_rows


def safe_count(n):
    return str(n) if n==0 or n>=11 else "<11"


def print_audit(evidence,queue,source,b_section):
    print("STEP76 LOCAL ONLY: ICD-10-PCS EXACT-CODE CLINICAL REVIEW QUEUE")
    print("Source rows are cohort memberships and can contain repeat procedures.")
    print("No additional patients or completed imaging is established.")
    print("Candidate labels are RULE-BASED, NOT clinically approved codes.")
    total=sum(item["observed_source_rows_cohort_memberships"] for item in queue)
    print("Candidate_exact_codes",len(queue),
          "candidate_source_rows_across_both_cohorts",total)
    for kind in ("MODE","SCOPE","P","YEAR"):
        print("\n",kind)
        for key,c in sorted(evidence.items()):
            if key[0]!=kind:
                continue
            print("|".join(key[1:]),
                  "candidate_source_rows",safe_count(c["candidate_rows"]),
                  "plausible_anatomy_rows",
                    safe_count(c["BRAIN_ANATOMY_CANDIDATE_rows"]+
                               c["HEAD_NECK_VESSEL_CANDIDATE_rows"]),
                  "unresolved_anatomy_rows",
                    safe_count(c["ANATOMY_UNRESOLVED_rows"]))
    print("\nSOURCE-YEAR BLOCK TRENDS within indexed inpatient section-B rows")
    for label,years in GROUPS.items():
        denominator=sum(b_section[(str(yy),str(p),"INDEX_IMP")]
                        for yy in years for p in (0,1))
        candidate=sum(evidence[("STRATUM",str(yy),str(p),"INDEX_IMP")]
                        ["candidate_rows"] for yy in years for p in (0,1))
        print(label,"review_only_candidates",safe_count(candidate),
              "all_B_section_source_rows",denominator,
              "candidate_per_B_source_row_pct",
              "%.2f"%(100*candidate/denominator) if denominator else "NA")
        for mode in MODALITY.values():
            n=sum(evidence[("MODE_YEAR",mode,str(yy))]["candidate_rows"]
                  for yy in years)
            if n:
                print("  ",mode,"all_scopes_review_only_rows",safe_count(n))
    print("These ratios are source coding representation, NOT patient imaging prevalence.")


def main():
    official,step74=s75.load_cached() # SHA-validated CMS public archives
    evidence,queue=assess(step74,official)
    b_rows=b_source_counts(s68.PRIVATE/s68.DB,step74)
    print_audit(evidence,queue,step74,b_rows)
    folder=s62._private_dir(PRIVATE)
    output=folder/REPORT
    if output.is_symlink() or output.exists():
        raise FileExistsError("Step76 private report exists; no overwrite")
    result={
        "policy":"STEP76_CODEBOOK_DISCOVERY_ONLY_V1",
        "source":"CMS public catalog archives cached in Step74",
        "source_step74_policy":"STEP74_DISCOVERY_ONLY_V1",
        "review_queue_LOCAL_ONLY":queue,
        "NOT_validated_patient_level_imaging":True,
        "clinical_review_required":True,
        "year_validity_by_discharge_date_required":True,
    }
    fd,tmp=tempfile.mkstemp(prefix=".step76_",dir=str(folder))
    try:
        with os.fdopen(fd,"w",encoding="utf8") as handle:
            json.dump(result,handle,indent=2,sort_keys=True)
            handle.write("\n")
        os.chmod(tmp,0o600)
        os.link(tmp,output)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print("\nPRIVATE review queue:",output)
    print("HANDOFF: TERMINAL OUTPUT ONLY. No ZIP or clinical source files.")


if __name__=="__main__":
    main()
