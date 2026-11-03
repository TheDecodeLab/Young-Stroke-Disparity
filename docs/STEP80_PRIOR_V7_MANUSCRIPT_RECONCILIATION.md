# Reconciliation of earlier V7 manuscript with rebuilt research-network study

**Status (2026-10-20): internal scientific provenance audit for
the Step80 manuscript.** This text lists only study design
differences and public citations; it does not publish old
source-derived patient counts, demographic subgroup data,
procedure-code frequencies, reviewer identities, author contact
details or protected patient data. The investigator supplied a
V7 Word manuscript and its original supplementary document
for local comparison. Do not upload either Word file to the
public repository.

## Core decision

The working Step80 manuscript is a **new EHR
ascertainment/encounter-attribution analysis**, rather than
a numerical continuation or independent validation of the
earlier V7 *Variation in Brain MRI and Vascular Imaging
Among Adults With Early-Onset Ischemic Stroke* manuscript.

An apparent imaging-care disparity is not established by
reproducing or revising clinical wording from V7. The revised
data architecture, inclusion criteria, encounter restrictions
and procedure-code semantics measure a different construct.

| Dimension | Earlier V7 manuscript + supplement | Current rebuilt Step62–80 research-network analysis | Editorial action |
|---|---|---|---|
| Data | TriNetX **Diamond** extract and external **NIS** inpatient sample | Distinct TriNetX **Research Network** export; no NIS rerun in this analysis | Do not transfer NIS contrasts into rebuilt Results |
| Period | 2018–2019 | Candidate 2016–2024 start years; contributing-site completeness not independently validated | Report own observation window and limitations |
| Age eligibility | Sex-dependent upper limits based on earlier young-stroke work | Uniform definitely eligible ages 18–50 primary; old sex-dependent upper limits only as overlapping sensitivity | Cite public data-driven age paper for historical rationale |
| Index diagnosis | Original V7 claimed principal ischemic stroke with ICD-9/10/H34.1 codes | Strict same-encounter ICD-10-CM I63/I63.* index IMP; P flag is **not adjudicated**, P=0 contains unmarked and secondary | Do not call P=0 confirmed secondary stroke |
| Index selection | Original V7 required availability of CT imaging | New cohort indexing independent of imaging-code ascertainment | Never introduce CT-conditioned eligibility into new denominator |
| Imaging time window | Diagnosis-centered ±7 days | Frozen exact indexed IMP interval; separate admission-day other-encounter and conservative preceding-ED/near-day capture sensitivities | Treat as different endpoint constructs |
| Modality vocabulary | Original supplementary code table covered head MRI/MRA/CTA/CT but a smaller code family | Exact 14-code CPT family includes head/neck CTA/MRA and diagnostic CT/MRI | Do not compare numeric rates as identical modalities |
| Main endpoint | Mean imaging **counts** and modality-specific receipt; vascular imaging composite | **Patient-level binary documented CPT14 code capture** by encounter definition | No carryover of count-model coefficients or composites |
| Regression | Original OLS for modality counts with age/CHA2DS2-VASc and other covariates | Exploratory grouped-binomial recorded-code GLMs; no reliable HCO site clustering or severity adjustment | Keep demographic-model results internal |
| Missing data | Original complete-case/listwise exclusion for several covariates | Unknown/unmapped demographic categories retained where possible | Do not reuse complete-case claims |
| External comparison | Original NIS described as independent comparison | NIS not reconstructed or reanalyzed in the Step62–80 pipeline | NIS is historical context, not validation |
| Interpretation | Original disparities in MRI/vascular imaging utilization | Difference in **code ascertainment and encounter attribution**, performed scan not verified | Remove clinical access/receipt conclusions |

## Content preserved from V7

- Young-onset stroke motivation and imaging modality
  distinctions, supported by the verified clinical review
  [Kakkar2021_StrokeImaging].
- The *published* data-driven young-stroke age
  rationale [Abedi2023_YoungStrokeAge]. The publication
  supports the historical eligibility sensitivity, not
  a rule that forces those age limits into the new
  primary cohort.
- Credible prior stroke-imaging literature,
  including existing source-checked
  [Vagal2017_AJNR] and [Wang2024_JACR].
- A reminder that imaging modality preferences
  could reflect diagnostic indications,
  setting and care pathways rather than simple
  access inequality. This is discussion context,
  not tested causal evidence.

These citations are added to the public-only
citation register and portable Zotero-ready
CSL-JSON/RIS/BibTeX. They have PubMed-verified
PMID and DOI metadata.

## Content intentionally NOT carried into Step80 Results

- The older Diamond MRI percentage, sex/race
  point estimates and regression coefficients.
- The NIS sample size, rate contrasts,
  significance tests and figures.
- The original nine-code supplementary
  category tables, original count outcomes,
  diagnosis-centered ±7-day episode claims,
  or any assertion that a CPT code proves
  the examination was completed.
- The original clinical claims that race or
  sex differences in performed imaging
  were established in the rebuilt cohort.
- The older IRB, funding, acknowledgments,
  author contributions and data-access
  declarations. These are study- and
  protocol-specific and require review
  before submission of a newly scoped paper.

## Authorship and reference-field provenance

The earlier main DOCX contains working Zotero
Word citation fields (20 citations and one
bibliography field on local inspection).
It should remain **unaltered as the historical
version of record**, including its author list,
corresponding-author structure and reference
links. It is unsafe to flatten or replace those
fields with manually typed bracketed reference
numbers and call them linked citations.

The Step80 Markdown manuscript and portable
bibliography are **not a continuation of those
embedded Zotero Word fields**. A future Word
submission file must explicitly build or link
Zotero fields and validate references after
the data-governance and scientific review gates.
The original author roster and corresponding
author designations are **proposals for confirmation**;
a different analytical contribution cannot
silently inherit contributions, declarations or
institutional approval wording from the earlier
study.

## Next scientific handoff

1. Repair stale reference-count tests after
   the intentional bibliography expansion.
2. Run Step80 on the investigator's approved
   local workstation. It will only read the
   immutable Step78 aggregate package and
   produce new restricted manuscript/figures.
3. Review the Step80 manuscript alongside
   the earlier V7 study context, while explicitly
   preventing results transfer between designs.
4. Obtain the author's scientific and coauthor
   approval later. Defer all CTSI, TriNetX
   and institutional outreach until the
   investigator explicitly requests it.

**Disclosure:** Original Step78 Table4
demographic subgroup rates remain withheld.
A locally generated manuscript is for internal
review only until data-owner/institutional
cross-table release procedures are complete.
