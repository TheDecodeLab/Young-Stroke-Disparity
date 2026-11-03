# Step 27: draft request to TriNetX / institutional data steward

**Prepared for investigator review. NOT SENT.** Confirm the appropriate
institutional data custodian and relevant authorization before sending.
This request seeks data availability and a schema only, not clinical rows.

## Concise email

Subject: Question about encounter-linked stroke data in our TriNetX Diamond export

Dear [Data Steward],

We are revisiting our study of MRI and vascular imaging during
hospitalizations for ischemic stroke in younger adults.

We have the original TriNetX Diamond export, but the diagnosis and
procedure tables appear to contain patient IDs and dates without a
shared hospitalization or encounter identifier. Because of this, we
cannot reliably determine whether imaging and the principal stroke
diagnosis belong to the same admission.

Could you please let us know whether an encounter- or
inpatient-claim-linked extract is available for our authorized
2018–2019 study period? Specifically, we would need:

1. A validated inpatient episode/claim identifier, admission and
   discharge dates, and inpatient versus outpatient/ED classification;
2. Diagnosis and procedure records linkable to that episode, including
   principal diagnosis status, service date and code system;
3. Documentation of MRI/CT/CTA/MRA claim coverage and any available
   de-identified site or facility identifier; and
4. Guidance on the export's patient selection, race/ethnicity
   completeness, data permissions and the approved access process.

For now, a data dictionary or a short discussion would be sufficient.
We are not requesting any patient-level files by email.

Thank you for your guidance.

Best,
Alireza

## Follow-up questions (if a feasible source exists)

Ask the custodian to confirm in writing:

- Is the encounter ID **shared across diagnosis and procedure
  tables**, or is an episode constructed from claims headers?
- How are transfers, overlapping encounters and ED imaging just
  before admission treated?
- Can principal stroke diagnosis be tied to the exact inpatient
  episode, and what do P, S and Unknown mean in the current export?
- Are inpatient radiology codes recorded as CPT, HCPCS, ICD-10-PCS,
  or other facility/professional billing formats? Which types
  systematically lack codes? Does the source include CTA/MRA neck?
- Is eligibility limited to an underlying stroke-derived export
  subset or otherwise prefiltered, and what is the population
  observation/enrollment or claims-capture period?
- Can birth-date/age-at-encounter be used in approved form? Is race
  or ethnicity more complete in an alternate authorized source?
- Are the required 2017 lookback and 2020 boundary records
  available? What are the restrictions and cost/effort of export?
- Can the analysis be done in a secure local workspace without
  redistributing patient-level data? What release rules apply?

## Do not attach

Do NOT attach the original 32+ GB ZIP, private SQLite indexes,
any patient-level Parquet, row excerpts, patient/postal identifiers,
unsuppressed cells or previously released fine-grained I63 results.

See [feasibility protocol](STEP27_HOSPITALIZATION_FEASIBILITY.md).
