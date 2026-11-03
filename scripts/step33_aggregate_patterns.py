"""Step 33: aggregate-only, descriptive recording-pattern comparison.

Inputs: Step31 and Step32 aggregate JSON reports ONLY. No TriNetX ZIP,
private SQLite, patient-level data, hypothesis tests, regressions or
disparity estimates. Cross-report disclosure review remains mandatory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

WINDOWS = ("0", "1", "3", "7")
STRATA = {
    "age_band": ("19-29", "30-39", "40-50"),
    "recorded_sex": ("Female", "Male"),
    "index_year": ("2018", "2019"),
}
MEASURES = (
    "any_head_n", "any_head_or_neck_n", "brain_MRI_n",
    "head_CTA_n", "head_CT_n", "head_MRA_n",
    "head_or_neck_CTA_n", "head_or_neck_MRA_n",
    "none_head_or_neck_n",
)


def must(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("Step 33 aggregate integrity check: " + reason)


def percentage(n: int, total: int) -> float:
    return round(n * 100.0 / total, 2)


def check_window(profile: dict, denominator: int, label: str) -> None:
    must(all(k in profile and isinstance(profile[k], int)
             and 0 <= profile[k] <= denominator for k in MEASURES),
         "incomplete values in " + label)
    must(profile["any_head_or_neck_n"] + profile["none_head_or_neck_n"]
         == denominator, "matched and unmatched do not partition " + label)
    must(profile["any_head_n"] <= profile["any_head_or_neck_n"],
         "head-only subset relation in " + label)
    for m in ("brain_MRI_n", "head_CTA_n", "head_CT_n", "head_MRA_n",
              "head_or_neck_CTA_n", "head_or_neck_MRA_n"):
        must(profile[m] <= profile["any_head_or_neck_n"],
             "modality count exceeds matched any in " + label)
    must(profile["head_CTA_n"] <= profile["head_or_neck_CTA_n"]
         and profile["head_MRA_n"] <= profile["head_or_neck_MRA_n"],
         "head and neck nesting in " + label)


def compare(step31: dict, step32: dict) -> dict:
    must(step31.get("stage") ==
         "STEP31_EXPANDED_IMAGING_AGGREGATE_RECONCILIATION"
         and step31.get("all_aggregate_checks_passed") is True
         and step31.get("clinical_inference_approved") is False
         and step31.get("cross_report_disclosure_review_required") is True
         and step31.get("original_source_rows_read") == 0
         and step31.get("patient_level_rows_read") == 0,
         "Step 31 provenance and scientific scope")
    must(step32.get("stage") ==
         "STEP32_READ_ONLY_RECORDING_HETEROGENEITY_QC"
         and step32.get("private_sqlite_source_verified") is True
         and step32.get("original_zip_rows_scanned") == 0
         and step32.get("private_patient_level_rows_exported") == 0
         and step32.get("clinical_inference_allowed") is False
         and step32.get("race_ethnicity_inference_allowed") is False
         and step32.get("publication_disclosure_review_required") is True,
         "Step 32 provenance and scientific scope")
    n = step31["study_cohort_n"]
    must(isinstance(n, int) and n > 0
         and n == step32["denominator"], "cohort denominator")
    must(step32["code_specific_event_rows_read"] > 0,
         "missing code-specific source event count")
    must(set(step31.get("per_window", {})) == set(WINDOWS),
         "Step 31 time windows")
    dimensions = step32.get("groupwise_coding_diagnostics", {})
    must(set(dimensions) == set(STRATA), "unexpected stratification")

    result = {}
    reference = {}
    for w in WINDOWS:
        ref = step31["per_window"][w]
        must(ref["denominator"] == n, "Step 31 window denominator")
        must(ref["expanded_with_any_included_code_n"] +
             ref["expanded_without_matching_included_code_n"] == n,
             "Step 31 window population partition")
        must(ref["head_only_with_any_included_code_n"] <=
             ref["expanded_with_any_included_code_n"],
             "Step 31 head subset")
        reference[w] = (
            ref["expanded_with_any_included_code_n"],
            ref["expanded_without_matching_included_code_n"],
            ref["head_only_with_any_included_code_n"],
        )

    for dimension, expected_labels in STRATA.items():
        info = dimensions[dimension]
        must(info.get("suppressed") is False,
             "dimension withheld by disclosure rules: " + dimension)
        rows = info.get("strata", [])
        must(len(rows) == len(expected_labels) and
             {row["stratum"] for row in rows} == set(expected_labels),
             "missing or extra strata in " + dimension)
        count = sum(row["denominator"] for row in rows)
        must(count == n and all(isinstance(row["denominator"], int)
             and row["denominator"] > 0 for row in rows),
             "dimension denominators do not reconcile " + dimension)
        totals_by_window = {}
        for w in WINDOWS:
            totals = {key: 0 for key in MEASURES}
            for row in rows:
                d = row["windows"][w]
                check_window(d, row["denominator"], dimension + " " +
                             row["stratum"] + " window " + w)
                for k in MEASURES:
                    totals[k] += d[k]
            must((
                totals["any_head_or_neck_n"],
                totals["none_head_or_neck_n"],
                totals["any_head_n"],
            ) == reference[w], "Step31 vs Step32 totals in " +
                 dimension + " window " + w)
            if dimension == "age_band":
                totals_by_window[w] = totals
            else:
                must(totals == result["age_band_totals"][w],
                     "inconsistent modality marginals across dimensions")
        if dimension == "age_band":
            result["age_band_totals"] = totals_by_window

        primary = sorted(rows, key=lambda row: expected_labels.index(row["stratum"]))
        metrics = []
        for row in primary:
            d = row["windows"]["1"]
            metrics.append({
                "stratum": row["stratum"],
                "denominator": row["denominator"],
                "head_only_any_code_n": d["any_head_n"],
                "head_only_any_code_percent": percentage(
                    d["any_head_n"], row["denominator"]),
                "expanded_head_plus_neck_any_code_n": d["any_head_or_neck_n"],
                "expanded_head_plus_neck_any_code_percent": percentage(
                    d["any_head_or_neck_n"], row["denominator"]),
                "expanded_no_matching_included_code_percent": percentage(
                    d["none_head_or_neck_n"], row["denominator"]),
                "head_CT_code_percent": percentage(
                    d["head_CT_n"], row["denominator"]),
                "brain_MRI_code_percent": percentage(
                    d["brain_MRI_n"], row["denominator"]),
                "head_CTA_code_percent": percentage(
                    d["head_CTA_n"], row["denominator"]),
                "head_MRA_code_percent": percentage(
                    d["head_MRA_n"], row["denominator"]),
            })
        result[dimension] = metrics

    # These pairwise contrasts describe UNADJUSTED coding frequency,
    # not causal, population or clinical-care differences.
    lookups = {dim: {row["stratum"]: row for row in rows}
               for dim, rows in result.items() if dim in STRATA}
    def pp(dim: str, a: str, b: str, measure: str) -> float:
        return round(lookups[dim][a][measure] -
                     lookups[dim][b][measure], 2)
    def contrasts(measure: str) -> dict:
        return {
            "age_19_29_minus_age_40_50_pp":
                pp("age_band", "19-29", "40-50", measure),
            "female_minus_male_pp":
                pp("recorded_sex", "Female", "Male", measure),
            "year_2019_minus_2018_pp":
                pp("index_year", "2019", "2018", measure),
        }
    head_coverage = {w: percentage(reference[w][2], n) for w in WINDOWS}
    expanded_coverage = {w: percentage(reference[w][0], n) for w in WINDOWS}
    catalog_increment = round(
        step31["per_window"]["1"]["expanded_minus_historical_coverage_percent_points"], 3)
    return {
        "stage": "STEP33_AGGREGATE_RECORDING_PATTERN_DESCRIPTIVES",
        "aggregate_inputs_only": True,
        "source_zip_records_read": 0,
        "private_sqlite_records_read": 0,
        "all_three_dimensions_reconciled": True,
        "denominator": n,
        "primary_window": "index date +/-1 calendar day",
        "working_primary_anatomy": "Head/brain CT MRI CTA MRA",
        "anatomic_sensitivity": "Head/brain plus cervical CTA MRA",
        "code_match_rates_by_group_head_only_and_expanded": {
            key: result[key] for key in STRATA
        },
        "unadjusted_head_only_differences_percentage_points":
            contrasts("head_only_any_code_percent"),
        "unadjusted_expanded_differences_percentage_points":
            contrasts("expanded_head_plus_neck_any_code_percent"),
        "window_head_only_any_code_percent": head_coverage,
        "window_expanded_any_code_percent": expanded_coverage,
        "expanded_any_code_percent_change_day0_to_plusminus7":
            round(100.0 * (reference["7"][0] - reference["0"][0]) / n, 2),
        "codebook_expansion_any_code_gain_at_plusminus1_pp": catalog_increment,
        "interpretation": (
            "Descriptive administrative code-frequency patterns; differences "
            "may reflect patient mix, observation, billing, clinical decisions, "
            "source capture or unrelated imaging. NOT differences in actual "
            "imaging access or quality of care."
        ),
        "clinical_inference_allowed": False,
        "demographic_disparity_inference_allowed": False,
        "cross_table_disclosure_review_required": True,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--step31", type=Path, required=True)
    p.add_argument("--step32", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path(
        "results/phase1/step33_recording_pattern_descriptives.json"))
    args = p.parse_args()
    prior = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (args.step31, args.step32)
    ]
    report = compare(*prior)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("Step 33 aggregate summaries reconciled:", args.output)
    print("No original ZIP or private SQLite records read. No clinical inference.")


if __name__ == "__main__":
    main()
