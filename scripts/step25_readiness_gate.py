"""Step 25: aggregate-only readiness gate for the provisional Diamond reanalysis.

Consumes *only* aggregate JSON reports from Steps 18-24. It opens no
patient-level SQLite records, original CSV files, or ZIP archives.
Passing arithmetic checks NEVER grants permission to model or publish.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

CLASSES = {
    "CT only": "ct_only_n",
    "CT + additional": "ct_and_additional_n",
    "Additional without CT": "advanced_no_ct_n",
    "None of four": "none_of_four_imaging_n",
}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("Aggregate reconciliation failed: " + message)


def gate(reconstruction: dict, temporal: dict, eligibility: dict) -> dict:
    check(reconstruction.get("stage") == "CHAINED_PROVISIONAL_RECONSTRUCTION"
          and reconstruction.get("completed_all_source_scans") is True,
          "full reconstruction stage/status")
    check(reconstruction.get("validated_admission_cohort") is False,
          "inpatient cohort must not be claimed validated")
    check(temporal.get("stage") == "STEP22_LOCAL_SQLITE_VALIDATION_ONLY"
          and temporal.get("previous_chained_report_compared") is True
          and temporal.get("previous_chained_report_discrepancies") == {},
          "Step 22 status or disagreement")
    check(eligibility.get("stage") == "STEPS23_24_ELIGIBILITY_AND_CODE_QC"
          and eligibility.get("step22_reference_compared") is True
          and eligibility.get("signature_reconciled") is True
          and eligibility.get("clinical_inference_allowed") is False,
          "Steps 23-24 status or source signature")

    stages = reconstruction["stages"]
    check(len(stages) == 3 and stages[0].get("scan_complete") is True,
          "source-stage completeness")
    diagnosis, demographics, imaging = stages
    source = diagnosis["aggregate_counters"]
    check(source["rows_scanned"] == diagnosis["declared_total_source_rows"],
          "diagnosis source row count versus manifest")
    all_index = diagnosis["distinct_principal_I63_candidate_patients"]
    eligible = demographics["eligible_n"]
    check(all_index == temporal["full_diagnosis_index_patients"]
          == demographics["matched_demographic_rows"],
          "diagnosis index counts")
    check(eligible == temporal["age_eligible_n"], "eligible totals")

    attr = eligibility["demographic_attrition"]
    groups = attr["exclusive_age_and_sex_attrition"]
    check(all(isinstance(n, int) and n >= 0 for n in groups.values()),
          "attrition counts must be nonnegative integers")
    check(sum(groups.values()) == all_index == attr["index_patients"]
          == attr["source_patients_matched_to_index"],
          "exclusive demographic attrition")
    check(groups["eligible_19_50"] == eligible
          == attr["saved_eligible_patients_reconciled_n"],
          "eligible cohort versus demographic audit")
    check(attr["original_patient_source_rows_verified"]
          == demographics["source_rows"],
          "demographic source row count")

    counts = imaging["aggregate_cohort_integrity"]
    check(counts["age_eligible_first_diagnosis_n"] == eligible,
          "imaging denominator")
    check(sum(counts[field] for field in CLASSES.values()) == eligible,
          "mutually exclusive imaging classes")
    check(counts["ct_n"] == counts["ct_only_n"] + counts["ct_and_additional_n"],
          "CT group arithmetic")
    check(temporal["matched_distinct_modality_days"]
          == imaging["distinct_modality_days_matched"],
          "modality-day count")
    windows = temporal["windows_inclusive_days_each_side"]
    for size in ("0", "1", "3", "7"):
        w = windows[size]
        check(w["total"] == eligible
              and sum(w[name] for name in CLASSES) == eligible,
              "time-window partition: " + size)
    wide = windows["7"]
    for label, field in CLASSES.items():
        check(wide[label] == counts[field], "seven-day category " + label)
    for modality in ("CT", "MRI", "CTA", "MRA"):
        check(wide[modality] == counts[modality.lower() + "_n"],
              "seven-day modality " + modality)
        check(all(windows[a][modality] <= windows[b][modality]
                  for a, b in (("0", "1"), ("1", "3"), ("3", "7"))),
              "monotonic window coverage for " + modality)

    detail = eligibility["diagnosis_and_imaging_diagnostics"]
    missing = detail["missing_race_ethnicity_by_imaging_group"]
    by_name = {item["imaging_class"]: item for item in missing}
    check(len(missing) == len(CLASSES) and set(by_name) == set(CLASSES),
          "missing demographic category")
    check(all(by_name[label]["patients"] == counts[field]
              for label, field in CLASSES.items()),
          "imaging group denominators in missingness audit")
    check(sum(item["race_unknown_or_missing_n"] for item in missing)
          == temporal["race_unknown_or_missing_n"], "race missingness")
    check(sum(item["ethnicity_unknown_or_missing_n"] for item in missing)
          == temporal["ethnicity_unknown_or_missing_n"], "ethnicity missingness")

    # Boolean warning only, NOT the residual count. Older fine-grained
    # reports can expose suppressed subtypes via complementary subtraction.
    detailed = detail.get("first_decimal_digit_audit_by_imaging", [])
    risk = any(entry.get("suppressed") for entry in detailed)
    # If the repaired coarse report is used, verify released groups add up.
    coarse = detail.get("coarse_icd10_group_by_imaging")
    if coarse is not None and all(not g["suppressed"] for g in coarse):
        check(len(coarse) == 2 and
              sum(g["eligible_total"] for g in coarse) == eligible,
              "coarse ICD summary does not cover entire eligible cohort")
        for label, field in CLASSES.items():
            check(sum(g["imaging_groups"][label] for g in coarse)
                  == counts[field], "coarse ICD classification " + label)

    percent = lambda n, d: round(100.0 * n / d, 2)
    return {
        "stage": "STEP25_AGGREGATE_READINESS_RECONCILIATION",
        "all_prior_aggregate_counts_reconciled": True,
        "zip_records_read": 0, "patient_level_sqlite_records_read": 0,
        "principal_I63_index_patients": all_index,
        "approximate_age_19_50_eligible_patients": eligible,
        "temporally_linked_ct_only_n": counts["ct_only_n"],
        "no_historical_listed_imaging_n": counts["none_of_four_imaging_n"],
        "descriptive_missingness_percent": {
            "birth_year_missing_or_invalid_among_index": percent(
                groups["missing_or_invalid_birth_year"], all_index),
            "race_unknown_among_eligible": percent(
                temporal["race_unknown_or_missing_n"], eligible),
            "ethnicity_unknown_among_eligible": percent(
                temporal["ethnicity_unknown_or_missing_n"], eligible),
            "none_of_four_historical_imaging_groups": percent(
                counts["none_of_four_imaging_n"], eligible),
        },
        "historical_fine_diagnosis_group_report_requires_disclosure_review": bool(risk),
        "ready_for_manuscript_inference": False,
        "unresolved_approval_gates": [
            "Define denominator: date-linked principal diagnosis versus confirmed hospitalization; no encounter ID in the export.",
            "Clinical review of I63/ICD-9/H34.1 index eligibility, lookback and principal-diagnosis meaning.",
            "Clinician-approved complete imaging CPT/HCPCS/PCS and head/neck modality codebook before rescans.",
            "Assess missing age, race, ethnicity and birth-year uncertainty before disparity models.",
            "Resolve data redistribution/Git history and complementary small-cell disclosure rules.",
        ],
        "recommended_next_action": (
            "Seek clinical protocol agreement and encounter-linked data where feasible. "
            "Do not launch more billion-row scans or model demographic disparities yet."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reconstruction", type=Path, required=True)
    p.add_argument("--temporal", type=Path, required=True)
    p.add_argument("--eligibility", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path(
        "results/phase1/step25_readiness_gate.json"))
    args = p.parse_args()
    inputs = [json.loads(path.read_text(encoding="utf-8")) for path in (
        args.reconstruction, args.temporal, args.eligibility)]
    output = gate(*inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("Aggregate-only readiness report:", args.output)
    print("All aggregate counts agree. Manuscript inference remains BLOCKED.")


if __name__ == "__main__":
    main()
