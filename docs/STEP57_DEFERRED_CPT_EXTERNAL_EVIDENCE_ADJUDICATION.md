# Step 57: External adjudication of the 13 deferred CPT-like reference entries

> **Current authority:** For Research Network analysis, follow the [active 2026 study plan](ACTIVE_RESEARCH_NETWORK_STUDY_PLAN.md) and [canonical code-to-reference register](references/IMAGING_CODE_CITATION_REGISTER.md). Earlier stage text below is historical/provisional and must not override the agreed A-primary/B-sensitivity policy, Diamond-only 2018–2019 distinction, source-code meaning limitations, and hard-blocked full scan.


**Evidence review completed 2026-10-18; locally confirmed 511 passing tests and Step57 8 exclusions + 5 holds.** The investigator's workstation confirmed **489 passing tests** after Step56 and **511** after Step57, and the existing private Step56 queue contains 13 CPT-labelled reference entries. All conclusions below concern **external code meaning**, not actually observed Research Network procedures. The submitted 13 code strings were discussed in this conversation, but no local terminology descriptions or private source files were uploaded.

## Literature-based decisions for diagnostic stroke neuroimaging

These codes **do not expand** the six predeclared MRI_BRAIN / CTA_HEAD / CTA_NECK / MRA_HEAD / MRA_NECK / CT_HEAD categories:

| Public code | Published meaning (short paraphrase) | Decision and evidence |
|---|---|---|
| 0398T | MRI-guided focused ultrasound *treatment* for intracranial movement disorders, not routine diagnostic MRI; replaced by 61715 effective 2025-01-01 | Exclude; [CMS coverage article](https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=58323&ver=12) |
| 0865T | Quantitative software analysis of brain MR, performed without a same-session diagnostic MRI | Exclude as a standalone MRI study; [AJNR 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11286008/) |
| 0866T | Quantitative software analysis adjunct to a same-session diagnostic MRI | Exclude as a standalone MRI study; paired 70551/70552/70553 can count if independently documented; [AJNR 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11286008/) and [CMS coding discussion](https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleId=60397&ver=5) |
| 61736, 61737 | Intracranial laser interstitial thermal therapy, MRI guidance when performed; therapeutic neurosurgery | Exclude; [61736](https://www.aapc.com/codes/cpt-codes/61736), [61737](https://www.aapc.com/codes/cpt-codes/61737) |
| 61751 | Stereotactic intracranial biopsy/aspiration/excision with CT or MRI guidance; procedure rather than diagnostic head CT/MRI | Exclude; [AAPC](https://www.aapc.com/codes/cpt-codes/61751) |
| 78814 | Limited-area **tumor PET/CT**, not diagnostic brain CT or vascular CTA | Exclude; [CMS historical PET code list](https://www.cms.gov/regulations-and-guidance/guidance/transmittals/downloads/r527cp.pdf) |
| 78830 | Radiopharmaceutical **SPECT/CT** localization, potentially of many anatomical regions; not brain CT or CTA | Exclude; [NLM VSAC CPT 2024](https://vsac.nlm.nih.gov/context/cs/codesystem/CPT/version/2024/code/78830/info) |

The 0865T/0866T codes were established in **January 2024** (AJNR); earlier years must not be assigned that coding. The 0398T→61715 replacement is **January 2025** (CMS). Historical effective dates for the other excluded codes are **not claimed to have been independently established for every Research Network service year**; exclusion follows their medical-service meaning irrespective of exact study-year availability.

The remaining five **CPT-labelled** codes from the locally generated queue are seven-digit numerical strings. [AMA's CPT overview](https://www.ama-assn.org/practice-management/cpt/cpt-code-set-basics-and-resources) describes CPT as five-character codes. The repository does not publish the locally extracted nonstandard identifiers; Step57 classifies them on the local workstation as **`hold_nonstandard_CPT_shape_CHECK_ORIGINAL_CODE_SYSTEM`**. Their meaning is **unknown** and they must NOT be automatically mapped to conventional imaging, declared clinically excluded, truncated to five digits, or treated as genuine CPT codes. They may be local identifiers, transformed codes or another terminology mislabeled as CPT, but none of those possibilities is verified.

## Implementation and local-only operation

- [Step57 public-source rule registry](../scripts/step57_external_cpt_adjudication.py): eight specific published code meanings, nonstandard shape holds, independent `defer_other_CPT_REQUIRES_EXACT_CODE_EVIDENCE` fallback.
- [Step57 synthetic tests](../tests/test_step57_external_cpt_adjudication.py): eight code exclusions; five seven-digit holds; source-report checks; rejected duplicates/forged provenance; restrictive private output permissions and no overwrites.
- The existing [Step54 CPT14 core](STEP54_PUBLIC_CPT14_LITERATURE_CODE_MEANING_REVIEW.csv) remains **unchanged** and is the proposed high-specificity *recorded-code* primary imaging definition.

Run on the institution-authorized study workstation:

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m pytest -q && python scripts/step57_external_cpt_adjudication.py prepare
```

This command reads only the private Step56 CPT queue and its reference-only summary, never the original Research Network ZIP or any patient, diagnosis, encounter, procedure or imaging result rows. It writes these **new, private, owner-only (0700 folder/0600 files) outputs** without overwriting any prior material:

`results/phase1/full_reconstruction_private/imaging_review/literature_adjudication/coverage_triage/external_evidence_adjudication/`

- `step57_deferred_CPT_external_evidence_LOCAL_ONLY.csv`: all locally deferred CPT-labelled rows with external evidence decision, original terminology description and source URL, including the five locally held identifiers. **Do not upload this private file to GitHub or an external service.**
- `step57_external_evidence_summary_LOCAL_ONLY.json`: status counts, SHA-256 of the Step56 input queue, and explicit flags showing zero clinical scans, zero authorizations changed, zero additions to the core.

**No clinical codebook sign-off is granted.** A published CPT label does not establish whether the Research Network `procedure.csv` row means a study actually occurred, and the observed frequency by code system remains **unknown**. The Step45 full-scan CLI is still disabled; draft PR #1 remains unmerged pending historical data governance review.

## Design decisions carried forward

- **Diamond:** separate 2018–2019 research period.
- **Research Network:** proposed start 2016-01-01, ending at the last adequately covered full calendar year determined by authorized observed-event completeness QA.
- **Imaging A primary:** code recorded under same inpatient IMP encounter.
- **Imaging B sensitivity:** unique, date-only provisional preceding ED association, with 0/1/2 calendar-day windows; not verified same-hospital imaging.
- **Age:** independent, overlapping uniform 18–50 and sex-specific men 18–52/women 18–54 definitions.
- **Further mapping:** independently verify exact SNOMED, ICD-10-PCS and HCPCS code semantics and actual EHR code-system usage before claiming broad imaging ascertainment. This cannot be inferred from the 3,270 reference candidates alone.
