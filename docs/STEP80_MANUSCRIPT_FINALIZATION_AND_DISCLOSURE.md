# Step80: Complete local-only manuscript, corrected figures, and disclosure request

**Status:** Public-source template, code, Zotero library, and
synthetic tests committed; **local Step80 execution not yet verified**.

## Investigator direction

Following successful Step78 (736 tests, privately created manuscript
tables/figures) and Step79 (745 tests, preliminary arithmetic
reconciliation, one Table4 small-event/complement disclosure flag),
the principal research paper concerns *measurement and
encounter attribution of documented CPT14 neuroimaging codes*,
**not** clinically confirmed brain imaging receipt or inequitable
stroke care. The main cohort is the definitely eligible ages 18–50
I63/IMP index, and the historical sex-dependent cohort overlaps it.

The investigator will review scientific, clinical and
statistical content after the manuscript is written.
Institutional output clearance and visual inspection
still require actions outside the program.

## What is completed in GitHub

1. `docs/MANUSCRIPT_ASCERTAINMENT_FULL_TEMPLATE.md` is a
   complete substantive manuscript, with title, structured
   abstract, introduction, exact cohort/index/coding
   methods, Results text slots, discussion, conclusions,
   figure legends, release restrictions, and seven
   verified references. Only **two dynamic
   slots** remain for filling the verified private
   aggregate numbers on the authorized workstation.
   An unpopulated source file is not publication-ready.
2. `scripts/step80_finalize_manuscript_local.py`
   reads ONLY immutable `Step78 draft_v1` internal
   outputs, first invokes the existing Step79
   integrity/disclosure screen, then creates an
   entirely new private manuscript review bundle.
   It refuses unknown disclosure flags or overwriting
   any previous review output.
3. Step80 creates a complete *numerically populated*
   internal manuscript, revised nominal-category
   Figure1 and Figure2 (unconnected dots, no
   continuous trend lines), private provenance
   hashes, disclosure request draft and
   portable Zotero reference library.
4. Table4 demographic subgroup P/capture rates are
   **omitted entirely from the internal manuscript
   and from the proposed disclosure scope**.
   Original Step78 Table4 is preserved unchanged
   and still internally restricted.
5. Zotero-ready `imaging_references.csl.json`,
   `imaging_references.ris`, and
   `imaging_references.bib` include
   independently PubMed-verified Vagal 2017,
   Wang 2024, Lewis 2023, Syed 2023 and
   An 2025 papers plus the core public CMS
   code and transition documentation.
   Cite identifiers are project-local Markdown
   references, **not linked Zotero Word fields**.

The script never reads patient-level data, source
ZIPs or clinic/HCO identifiers. It writes private
markdown/PDF-independent figure artifacts,
not a Word DOCX.

## Exact figure paths

Previously completed Step78 original figures:

```text
results/phase1/full_reconstruction_private/step78_paper_exhibits_private/draft_v1/figure1_coded_capture_by_encounter.png
results/phase1/full_reconstruction_private/step78_paper_exhibits_private/draft_v1/figure2_source_quality_standardization.png
```

Proposed replacement figures once Step80 succeeds:

```text
results/phase1/full_reconstruction_private/step80_manuscript_private/review_v1/figure1_code_capture_review_v1.png
results/phase1/full_reconstruction_private/step80_manuscript_private/review_v1/figure2_unconnected_contrasts_review_v1.png
```

Both are **LOCAL ONLY** and must be visually inspected on
the authorized workstation. Figure2 uses unconnected
categorical marks because distinct encounter definitions
are not a time series.

## Complete internal manuscript path (after local run)

```text
results/phase1/full_reconstruction_private/step80_manuscript_private/review_v1/MANUSCRIPT_INTERNAL_REVIEW.md
```

The private package also includes:
`DISCLOSURE_REVIEW_REQUEST_DRAFT.md` (counts-free request
for an authorized internal reviewer),
`TABLE4_WITHHELD_README.md`,
`FIGURE_QA_README.md`,
portable reference RIS/CSL-JSON/BibTeX
and `PROVENANCE_INTERNAL.json`.

## One local command

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step80_finalize_manuscript_local.py
  python -m pytest -q tests/test_step80_finalize_manuscript_local.py
  python -m pytest -q
  python scripts/step80_finalize_manuscript_local.py
)
```

The command is fail-fast, generates a new immutable
`review_v1`, and will not modify Step78 `draft_v1`.
**Return TERMINAL OUTPUT ONLY**, not manuscripts,
tables, figure images, clinical code review sheets,
source databases, or raw ZIPs.

## Institutional clearance and final review

**Permission is NOT obtained by this step.**
The output packet is a ready-for-authorized-submission
request; only the institutional data custodian/
TriNetX Research Network governance process
can authorize release of source-derived numbers.
The investigator must identify the appropriate
reviewer/office and submit the approved packet.
This assistant cannot self-certify disclosure safety.
A smaller Table4 does not automatically become
shareable just because its flagged percentages
were removed; cross-table subtraction and site
representation must be assessed across all proposed
exhibits. The review scope here is *main Table1,
Table2 and Figures1–2*, with Table3/Table5 held.

Clinical/statistical coauthor review and a
human inspection of both final figures remain
the remaining scientific gates. Any later final
Word DOCX will require the Zotero Word-field
insertion/validation workflow, not treating
plain Markdown citation keys as connected fields.
