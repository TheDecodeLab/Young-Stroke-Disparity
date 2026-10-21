#!/usr/bin/env python3
"""Step80: finalize a PRIVATE quantitative manuscript and improved figures.

Consumes ONLY the immutable Step78 draft_v1 package and the public-only
manuscript/reference templates. No raw patient-level database or source ZIP.
Withholds disclosure-sensitive Table4 rates entirely. Does not certify
institutional disclosure or create live Zotero Word fields.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from collections import defaultdict

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step78_paper_results_bundle as s78
    from scripts import step79_manuscript_exhibit_integrity as s79
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step78_paper_results_bundle as s78
    import step79_manuscript_exhibit_integrity as s79

ROOT=s62.ROOT
SOURCE=s78.DEST/"draft_v1"
OUT=ROOT/"results/phase1/full_reconstruction_private/step80_manuscript_private"
REVIEW="review_v1"
TEMPLATE=ROOT/"docs/MANUSCRIPT_ASCERTAINMENT_FULL_TEMPLATE.md"
CSL=ROOT/"docs/references/imaging_references.csl.json"
RIS=ROOT/"docs/references/imaging_references.ris"
BIB=ROOT/"docs/references/imaging_references.bib"
EXPECTED_FLAG="Table4_derived_small_event_or_complement"
PLOT_LABELS={
    "INDEX_IMP":"Index inpatient",
    "INDEX_IMP_OR_SAME_DAY_OTHER":"Index + other same-day encounter",
    "INDEX_IMP_OR_UNIQUE_ED":"Index + unique preceding ED",
    "INDEX_IMP_OR_ED_PRE2_DAY0":"Index + broader near-day screen",
}


def require(expr,what):
    if not expr:
        raise ValueError("Step80 validation: "+what)


def fmt_n(value):
    return format(int(value),",")


def fmt_pct(value):
    return f"{float(value):.2f}%"


def fmt_diff(value):
    return f"{float(value):+.2f}"


def order_rows(rows,cohort):
    mapping={(r["cohort"],r["endpoint_key"]):r for r in rows}
    expected=[(cohort,key) for key in PLOT_LABELS]
    require(all(k in mapping for k in expected),"missing endpoint in "+cohort)
    return [mapping[k] for k in expected]


def extract(tables,cohort=s78.PRIMARY):
    """Only main index/encounter aggregated results enter prose.

    No Table4 demographic category detail and no unreviewed Table5
    model contrast enter the manuscript.
    """
    t1=tables["t1"];t2=tables["t2"]
    pmap={(r["cohort"],int(r["P_indicator"])):r for r in t1}
    require((cohort,0) in pmap and (cohort,1) in pmap,
            "missing primary cohort P groups")
    group0,group1=pmap[cohort,0],pmap[cohort,1]
    rows=order_rows(t2,cohort)
    base,day,ed,broad=rows
    n0=int(group0["denominator"]);n1=int(group1["denominator"])
    require(n0+n1>0 and int(base["P0_n"])==n0 and
            int(base["P1_n"])==n1,"cohort denominator mismatch")
    for p,g in ((0,group0),(1,group1)):
        require(int(base[f"P{p}_documented_code_n"])==
                int(g["index_inpatient_CPT14_n"]),
                "original inpatient CPT14 mismatch")
    header=(
        "| Eligible coded-encounter definition | P=0, n/N (%) | "
        "P=1, n/N (%) | Crude P=1−P=0 (pp) | "
        "Year × encounter-QA standardized difference (pp) |\n"
        "|---|---:|---:|---:|---:|"
    )
    table=[header]
    for row in rows:
        a,b=(int(row[f"P{p}_documented_code_n"]) for p in (0,1))
        table.append(
          "| "+PLOT_LABELS[row["endpoint_key"]]+" | "+
          f"{fmt_n(a)}/{fmt_n(n0)} ({fmt_pct(row['P0_crude_pct'])}) | "+
          f"{fmt_n(b)}/{fmt_n(n1)} ({fmt_pct(row['P1_crude_pct'])}) | "+
          fmt_diff(row["P1_minus_P0_crude_pp"])+" | "+
          fmt_diff(row["P1_minus_P0_common_year_quarantine_pp"])+" |"
        )
    main_table="\n".join(table)
    h0=int(group0["any_ambiguous_encounter_patient_n"])
    h1=int(group1["any_ambiguous_encounter_patient_n"])
    results=f"""### Study population and recording context

The uniform definitely age-eligible 18–50 cohort comprised
{fmt_n(n0+n1)} indexed I63-coded inpatient patients:
{fmt_n(n0)} with P=0 and {fmt_n(n1)} with P=1.
The unvalidated P indicator separated diagnosis-recording
categories and was not a clinically adjudicated
principal-versus-secondary stroke classification.
At least one emergency/inpatient encounter key
was quarantined for source-record ambiguity in
{fmt_n(h0)} P=0 patients
({fmt_pct(group0['any_ambiguous_encounter_patient_pct'])})
and {fmt_n(h1)} P=1 patients
({fmt_pct(group1['any_ambiguous_encounter_patient_pct'])}).
This indicator is patient-level and does not mean that
the particular index encounter was faulty.

### Primary CPT14 code-capture endpoint

Among P=0 patients, {fmt_n(base['P0_documented_code_n'])}
({fmt_pct(base['P0_crude_pct'])}) had at least one
CPT14 neuroimaging code recorded on the index inpatient
encounter. For P=1, the corresponding count was
{fmt_n(base['P1_documented_code_n'])}
({fmt_pct(base['P1_crude_pct'])}). The crude
P=1 minus P=0 difference in *documented inpatient
procedure-code capture* was
{fmt_diff(base['P1_minus_P0_crude_pp'])} percentage points.
These are not confirmed imaging-examination rates.

### Additional encounter-code definitions

Retaining the same patient denominators, allowing a CPT14
code on any other encounter on the admission date produced
recorded-code capture of {fmt_pct(day['P0_crude_pct'])}
(P=0) and {fmt_pct(day['P1_crude_pct'])} (P=1).
The crude P=1 minus P=0 difference was
{fmt_diff(day['P1_minus_P0_crude_pp'])} percentage
points. After descriptive standardization to the
same calendar-year × any-key encounter-quarantine
distribution, the difference was
{fmt_diff(day['P1_minus_P0_common_year_quarantine_pp'])}
percentage points. The corresponding year-only
standardized difference was
{fmt_diff(day['P1_minus_P0_common_year_only_pp'])}
percentage points; restricting to patients
without any quarantined encounter key gave
{fmt_diff(day['P1_minus_P0_no_ambiguous_pp'])}
percentage points. This sensitivity to source mix
does not establish a causal mechanism.

Under the reciprocal-uniqueness preceding emergency
link definition, capture was
{fmt_pct(ed['P0_crude_pct'])} in P=0 and
{fmt_pct(ed['P1_crude_pct'])} in P=1; the
crude group difference was
{fmt_diff(ed['P1_minus_P0_crude_pp'])}
percentage points and the year × source-quality
standardized difference was
{fmt_diff(ed['P1_minus_P0_common_year_quarantine_pp'])}.
The broader near-admission ED/other-encounter
screen gave a crude contrast of
{fmt_diff(broad['P1_minus_P0_crude_pp'])}
percentage points and a standardized contrast of
{fmt_diff(broad['P1_minus_P0_common_year_quarantine_pp'])}
percentage points. These are separate
**data-attachment scenarios**, not independently
validated episode-specific neuroimaging.

### Table 2. Documented CPT14 code capture by encounter rule

{main_table}

*P denotes an unvalidated I63 principal diagnosis
recording indicator; P=0 includes blank, non-P and
secondary labels. Rates use frozen indexed patients
as denominators. Standardization uses pooled
calendar-year × patient-level any-quarantined-key
weights, not a causal model. More inclusive
encounter rules have unverified HCO/episode
attribution and none confirms scan performance.*

### Sensitivity and exploratory demographic findings

The historical sex-dependent upper-age eligibility
cohort was analyzed separately because its
membership overlaps the primary cohort. Exploratory
sex/race/ethnicity models and source-category
completeness assessments were completed locally;
the available data did not support validated
hospital-clustered inference or a clinical
imaging-care disparity conclusion. Category-specific
P and imaging-capture rates are omitted from
this manuscript pending institutional disclosure
review, following the Step79 small-event/complement
screen.

### Alternative ICD-10-PCS representation

An exact-code CMS title review identified a
restricted set of possible inpatient CT/MR
codes. Source procedure rows were not
interpretable as additional distinct patients.
Even an intentionally extreme upper bound
for adding the candidate PCS source rows did
not remove the index-inpatient CPT14 P contrast.
No PCS code was reclassified as a verified
patient-level imaging outcome.
"""
    ar=f"""The primary cohort comprised {fmt_n(n0+n1)} indexed
patients (P=0, {fmt_n(n0)}; P=1, {fmt_n(n1)}).
On the index inpatient encounter, documented
CPT14 capture was {fmt_pct(base['P0_crude_pct'])}
(P=0) versus {fmt_pct(base['P1_crude_pct'])}
(P=1), a crude P=1 minus P=0 difference of
{fmt_diff(base['P1_minus_P0_crude_pp'])} percentage
points. Including codes recorded under another
encounter on the admission calendar date changed
the corresponding difference to
{fmt_diff(day['P1_minus_P0_crude_pp'])}
percentage points. Standardization to pooled
year × encounter-key-quality strata gave
{fmt_diff(day['P1_minus_P0_common_year_quarantine_pp'])}
percentage points for that broader definition.
This sensitivity illustrates ascertainment
differences, not confirmed imaging care.
"""
    return {"ABSTRACT_RESULTS":" ".join(ar.split()),"RESULTS_TEXT":results}, rows


def fill_template(template,values,refs):
    require(template.count("{{ABSTRACT_RESULTS}}")==1 and
            template.count("{{RESULTS_TEXT}}")==1,
            "template must declare exactly two population result slots")
    used=set(re.findall(r"@([A-Za-z0-9_]+)",template))
    known={r["id"] for r in refs}
    require(used<=known,
            "manuscript has references missing from portable CSL library")
    filled=template
    for k,v in values.items():
        filled=filled.replace("{{"+k+"}}",v)
    require(not re.search(r"{{[A-Za-z_]+}}",filled),
            "unfilled manuscript result slot")
    for value in ("Table 4 (WITHHELD)","NOT CLEARED FOR EXTERNAL DISCLOSURE"):
        require(value in filled,"manuscript missing disclosure notice")
    return filled


def figures(rows,folder):
    """Horizontal unconnected points on NOMINAL encounter definitions."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    require(len(rows)==4,"expected four nominal encounter definitions")
    names=[PLOT_LABELS[r["endpoint_key"]] for r in rows]
    labels=list(reversed(names))
    dat=list(reversed(rows))
    y=list(range(len(labels)))
    f,ax=plt.subplots(figsize=(11,5.9))
    for p,shift,mark,color in ((0,-0.13,"o","#31688e"),(1,0.13,"s","#c27b39")):
        values=[float(r[f"P{p}_crude_pct"]) for r in dat]
        ax.scatter(values,[v+shift for v in y],
                   s=90,marker=mark,color=color,
                   label=f"I63 principal-record flag P={p}")
    ax.set_xlim(0,100)
    ax.set_yticks(y,labels)
    ax.set_xlabel("Indexed patients with a documented CPT14 code (%)")
    ax.set_title("Recorded code capture depends on encounter definition",
                 fontsize=13,loc="left")
    ax.grid(axis="x",alpha=.19)
    ax.set_axisbelow(True)
    for sp in ("top","right","left"):
        ax.spines[sp].set_visible(False)
    f.subplots_adjust(left=.36,right=.96,top=.89,bottom=.30)
    f.legend(loc="center",bbox_to_anchor=(.68,.135),
             ncol=2,frameon=False,fontsize=9)
    f.text(.36,.05,"Codes are not verified scans; other encounters may differ in site or episode.",
           fontsize=8.6,color="#525252")
    f.savefig(folder/"figure1_code_capture_review_v1.png",dpi=240)
    plt.close(f)

    f,ax=plt.subplots(figsize=(11,5.9))
    crude=[float(r["P1_minus_P0_crude_pp"]) for r in dat]
    adjusted=[float(r["P1_minus_P0_common_year_quarantine_pp"]) for r in dat]
    ax.scatter(crude,[v-.13 for v in y],marker="o",
               color="#31688e",s=90,label="Unstandardized")
    ax.scatter(adjusted,[v+.13 for v in y],marker="s",
               color="#c27b39",s=90,
               label="Common year × source-quality mix")
    ax.axvline(0,color="#666666",lw=1)
    ax.set_yticks(y,labels)
    ax.set_xlabel("P=1 minus P=0 recorded-code capture (percentage points)")
    ax.set_title("Categorical encounter rules: crude and standardized differences",
                 fontsize=13,loc="left")
    ax.grid(axis="x",alpha=.19)
    ax.set_axisbelow(True)
    extent=max(abs(v) for v in crude+adjusted)+3
    ax.set_xlim(-extent,extent)
    for sp in ("top","right","left"):
        ax.spines[sp].set_visible(False)
    f.subplots_adjust(left=.36,right=.96,top=.89,bottom=.30)
    f.legend(loc="center",bbox_to_anchor=(.68,.135),
             ncol=2,frameon=False,fontsize=9)
    f.text(.36,.05,"Source-composition standardization is descriptive, not causal.",
           fontsize=8.6,color="#525252")
    f.savefig(folder/"figure2_unconnected_contrasts_review_v1.png",dpi=240)
    plt.close(f)


def disclosure_packet():
    return """# Institutional research-network results disclosure request

**Draft status: FOR AUTHORIZED INVESTIGATOR SUBMISSION; NOT APPROVED**

**Study:** Encounter attribution and documented neuroimaging-code capture
among young adults with candidate I63-coded stroke hospitalizations.

**Purpose:** Seek institutional/network permission to use summary
results, main Tables 1–2, and revised categorical Figures 1–2
in a scientific manuscript describing EHR *ascertainment* rather
than clinically confirmed imaging receipt or inequity.

**Data source/security:** TriNetX Research Network export
on an institutionally authorized workstation. All raw records,
indexed patient data, exact observed procedure code review lists,
and internal model inputs are withheld. Only approved aggregate
outputs will be used outside the authorized environment.

**Proposed main exhibits:** Table 1 frozen
indexed cohort/P recording and any-key source QA; Table 2
four recorded-CPT14 capture definitions and their crude/
descriptively standardized differences; Figures 1–2
summarizing those same aggregate definitions.

**Withhold:** Original Table 4 demographic P/capture rates
because Step79 detected an inferable small event/complement risk.
Table 3 year×quality cell detail and Table 5 demographic
model contrasts remain internal pending separate decisions.
The two age cohorts overlap and should not be summed.

**Requests to institutional reviewer:**
1. Confirm applicable data-use/network publication
   and minimum-cell rules.
2. Review Table 1, Table 2 and both figures jointly,
   including back-calculable nested differences,
   complements, repeated margins and provider-level risk.
3. Confirm whether any primary/secondary
   complementary suppression, rounding, pooling or
   withholding is needed.
4. Confirm that excluding original Table 4 and
   exploratory demographic models is sufficient
   for the proposed release scope.
5. State written release conditions and responsible
   reviewer/committee approval before outside circulation.

**Approval state:** PENDING. No approval or permission
is presumed from software tests, automatic suppression,
or manuscript drafting. This packet includes NO source counts.
"""


def main():
    tables,manifest,_=s79.read_private_bundle(SOURCE)
    flags=s79.audit(tables)
    require(set(flags)<={EXPECTED_FLAG},
            "unreviewed additional disclosure-risk tag; abort manuscript package")
    if EXPECTED_FLAG in flags:
        print("Disclosure category: Table4 rates withheld; manual review pending")
    template=TEMPLATE.read_text(encoding="utf8")
    refs=json.loads(CSL.read_text(encoding="utf8"))
    values,primary_rows=extract(tables)
    manuscript=fill_template(template,values,refs)
    require(RIS.is_file() and BIB.is_file(),
            "portable Zotero reference exports missing")

    dest=s62._private_dir(OUT)
    final=dest/REVIEW
    require(not final.exists() and not final.is_symlink(),
            "review_v1 already exists; immutable, refuse overwrite")
    stage=Path(tempfile.mkdtemp(prefix=".stage_",dir=str(dest)))
    try:
        (stage/"MANUSCRIPT_INTERNAL_REVIEW.md").write_text(
            manuscript,encoding="utf-8")
        (stage/"DISCLOSURE_REVIEW_REQUEST_DRAFT.md").write_text(
            disclosure_packet(),encoding="utf-8")
        (stage/"TABLE4_WITHHELD_README.md").write_text(
            "Original demographic Table4 rates have NOT been copied to "
            "this candidate manuscript. No data subset is certified "
            "for public release. Manual cross-table review pending.\n",
            encoding="utf-8")
        (stage/"FIGURE_QA_README.md").write_text(
            "Two NEW internal figures use separate nominal-category "
            "points, without trend lines. Inspect label clipping, "
            "legend placement, axis scaling, colors and all percentages "
            "against frozen local Step78 Table2 before release.\n",
            encoding="utf-8")
        figures(primary_rows,stage)
        shutil.copyfile(RIS,stage/"references_zotero_import.ris")
        shutil.copyfile(CSL,stage/"references_zotero_import.csl.json")
        shutil.copyfile(BIB,stage/"references_zotero_import.bib")
        inventory=sorted(p.name for p in stage.iterdir())
        check={
            "source":"Step78 immutable draft_v1",
            "source_policy":manifest["policy"],
            "manuscript_scope":"documented CPT14 ascertainment only",
            "withheld_table4_source_percentages":True,
            "formal_disclosure_approval":False,
            "clinical_review_completed":False,
            "figure_visual_review_completed":False,
            "contains_private_aggregate_numbers":True,
            "source_sha256":{
                name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()
                for name in s79.TABLES.values()
            },
            "artifacts":inventory,
        }
        (stage/"PROVENANCE_INTERNAL.json").write_text(
            json.dumps(check,indent=2,sort_keys=True)+"\n",encoding="utf8")
        for p in stage.iterdir():
            require(p.is_file() and p.stat().st_size>0,
                    "incomplete staged manuscript artifact")
            os.chmod(p,0o600)
        os.chmod(stage,0o700)
        require(not final.exists(),"another process created review_v1")
        stage.rename(final)
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    print("STEP80 LOCAL ONLY: FULL MANUSCRIPT AND REVISED FIGURES CREATED")
    print("Results and structured abstract populated from frozen Step78 tables: YES")
    print("Full Introduction, Methods, Discussion, Conclusions and references: YES")
    print("Current Table4 subgroup capture/P percentages: WITHHELD")
    print("Figure1 and unconnected nominal-category Figure2: CREATED")
    print("CPT14 code definition and HCO/episode caveats: PRESERVED")
    print("External disclosure: NOT APPROVED; request draft prepared")
    print("Private review directory:",final)
    print("HANDOFF: TERMINAL OUTPUT ONLY; no manuscript, data or plots uploaded.")


if __name__=="__main__":
    main()
