# Cohort selection audit: critical finding

The Step 7 summary includes 23,232 patients aged 19-50. Exactly 6,270 received neither CTA nor MRA, and all 6,270 received MRI. No saved patient lacks MRI, CTA and MRA simultaneously.

The historical notebook selects CT patients, removes CT rows, and groups the remaining MRI, CTA and MRA records. Consequently, an eligible CT-only patient has no surviving row in the saved cohort. The number of omitted CT-only patients cannot be recovered from the present derived table.

The resulting imaging rates and sex differences are conditional on receiving at least one of MRI/CTA/MRA and do not estimate utilization in the intended stroke population. Halt inferential modeling using the derived cohort.

Reconstruct an index cohort from the original principal ischemic-stroke diagnosis or encounter records, independently of imaging. Verify CT eligibility for each index event. Left-join MRI, CTA and MRA events, retaining CT-only cases with zero values. Check event windows, uniqueness and attrition by group before refitting any models. The separate NIS replication analysis also requires source-code and survey-method validation.

**Status: scientific stop pending cohort reconstruction.**

## Possible recovery from an earlier intermediate

Notebook cell 9 saves `df_merged_age.parquet` **before** cell 11
removes CT rows. If this intermediate file still exists in approved
local storage, it may retain eligible CT-only patients. It is a useful
first recovery candidate, **not automatically a correct cohort**: its
procedure-to-diagnosis join can be many-to-many, and its drop-duplicates
step may affect the index-event mapping. Validate linkage and timing
carefully against the original diagnosis and procedure exports before
relying on it.

Please share the file's schema/columns and aggregate CT-only counts,
not patient records, while data-use permissions remain uncertain.
