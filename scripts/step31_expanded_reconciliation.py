"""Step 31: reconcile previously completed code-specific extraction reports.

This script reads THREE AGGREGATE JSONs only (no ZIP/SQLite or patient
identifiers). A successful arithmetic validation is not clinical
validation, admission linkage, or a license to estimate disparities.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

WINDOWS = ("0", "1", "3", "7")
CLASS_KEYS = ("CT only", "CT + additional",
              "Additional without CT", "None of four")
MODALITIES = ("CT", "MRI", "CTA", "MRA")


def ensure(ok: bool, label: str) -> None:
    if not ok:
        raise ValueError("Step 31 reconciliation failed: " + label)


def _partition(counts: dict, n: int, name: str) -> None:
    ensure(counts.get("total") == n and counts.get("suppressed", False) is False,
           name + ": denominator or suppression")
    ensure(all(isinstance(counts.get(k), int) and 0 <= counts[k] <= n
               for k in (*CLASS_KEYS, *MODALITIES)), name + ": missing/invalid counts")
    ensure(sum(counts[k] for k in CLASS_KEYS) == n,
           name + ": mutually exclusive classes")
    ensure(counts["CT"] == counts["CT only"] + counts["CT + additional"],
           name + ": CT allocation")


def reconcile(preflight: dict, expanded: dict, legacy: dict) -> dict:
    ensure(preflight.get("stage") == "STEP28_PREFLIGHT_ONLY"
           and preflight.get("procedure_rows_scanned") == 0,
           "preflight must have scanned zero procedure records")
    ensure(preflight.get("number_of_candidate_codes") == 14
           and all(row.get("clinical_review") == "evidence_reviewed"
                   for row in preflight["candidate_codes"]),
           "review basis or catalog size")
    ensure(expanded.get("stage") == "STEP28_EXPANDED_CODE_EXTRACTION_TEMPORAL_PROXY"
           and expanded.get("review_basis") ==
           "published_evidence_only_no_independent_clinician_signoff",
           "extraction provenance")
    ensure(expanded.get("existing_data_use_permission_attested_by_local_operator") is True,
           "local operator permission attestation absent")
    ensure(expanded.get("manifest_row_count_verified") is True
           and expanded.get("source_procedure_rows_scanned") ==
           preflight.get("source_procedure_rows_declared"),
           "source procedure row count")
    # In the Step28 report, approved_codebook_sha256 is a LEGACY KEY NAME,
    # and represents codebook ID only, NOT clinician/institutional approval.
    ensure(expanded.get("approved_codebook_sha256") ==
           preflight.get("codebook_sha256"), "codebook fingerprint")
    ensure(expanded.get("encounter_validated") is False
           and expanded.get("ready_for_manuscript_inference") is False
           and expanded.get("scientific_inference_and_publication_approved") is False,
           "source cannot be reported as admission-validated or manuscript-ready")
    ensure(legacy.get("stage") == "STEP22_LOCAL_SQLITE_VALIDATION_ONLY"
           and legacy.get("previous_chained_report_compared") is True
           and legacy.get("previous_chained_report_discrepancies") == {},
           "legacy Step22 stage")
    n = preflight["private_indexed_age_19_50_patients"]
    ensure(n == expanded.get("eligible_diagnosis_first_patients")
           == legacy.get("age_eligible_n") and n > 0,
           "cohort denominator")
    ensure(expanded.get("retained_legacy_patient_modality_days") ==
           legacy.get("matched_distinct_modality_days"),
           "historical modality-day preservation")
    ensure(expanded.get("matched_code_specific_patient_days", 0) >=
           expanded.get("retained_legacy_patient_modality_days", 0),
           "matched event count below legacy unique modality days")
    ensure(expanded.get("aggregate_disclosure_review_required") is True,
           "must preserve cross-table disclosure review requirement")
    generic = expanded["windows_inclusive_days_each_side"]
    profiles = expanded["anatomic_profiles_by_window"]
    earlier = legacy["windows_inclusive_days_each_side"]
    for keys in (generic, profiles, earlier):
        ensure(all(w in keys for w in WINDOWS), "required sensitivity windows missing")

    summary = {}
    for window in WINDOWS:
        old = earlier[window]
        head = profiles[window]["head_only_primary"]
        wide = profiles[window]["head_plus_neck_sensitivity"]
        all_codes = generic[window]
        ensure(profiles[window].get("suppressed") is False,
               "anatomic profile unavailable/suppressed in window " + window)
        for label, d in (("legacy", old), ("head", head),
                         ("expanded", wide), ("all_codes", all_codes)):
            _partition(d, n, window + "/" + label)
        ensure(all(wide[k] == all_codes[k] for k in (*MODALITIES, *CLASS_KEYS)),
               "generic modal summary versus expanded anatomical summary")
        ensure(head["CT"] == old["CT"] == wide["CT"]
               and head["MRI"] == old["MRI"] == wide["MRI"],
               "structural CT/MRI should not change")
        ensure(head["CTA"] == old["CTA"], "head CTA historical code was lost")
        ensure(head["MRA"] >= old["MRA"], "new MRA head code cannot reduce matches")
        ensure(wide["CTA"] >= head["CTA"] and wide["MRA"] >= head["MRA"],
               "neck outcomes must be supersets of head outcomes")
        ensure(old["None of four"] >= head["None of four"]
               >= wide["None of four"], "adding codes cannot reduce match coverage")
        neck = profiles[window]["neck_without_head_cta_mra"]
        ensure(wide["CTA"] - head["CTA"] == neck["CTA neck without CTA head"],
               "CTA neck-only patient increment")
        ensure(wide["MRA"] - head["MRA"] == neck["MRA neck without MRA head"],
               "MRA neck-only patient increment")
        deltas = {
            "additional_any_included_code_vs_historical_n":
                old["None of four"] - wide["None of four"],
            "new_head_mra_patient_matches_n": head["MRA"] - old["MRA"],
            "new_neck_cta_patient_matches_n": wide["CTA"] - head["CTA"],
            "new_neck_mra_patient_matches_n": wide["MRA"] - head["MRA"],
        }
        ensure(all(v >= 0 for v in deltas.values()),
               "negative expansion difference")
        # Entire window's additive group is suppressed if a positive
        # difference is small. Comparison against other public tables
        # still needs an independent institution-level disclosure audit.
        safe = not any(0 < v < 11 for v in deltas.values())
        entry = {
            "denominator": n,
            "legacy_with_any_included_code_n": n-old["None of four"],
            "head_only_with_any_included_code_n": n-head["None of four"],
            "expanded_with_any_included_code_n": n-wide["None of four"],
            "expanded_without_matching_included_code_n": wide["None of four"],
            "expanded_unmatched_percent": round(
                wide["None of four"] / n * 100, 2),
            "expanded_minus_historical_coverage_percent_points": round(
                (old["None of four"] - wide["None of four"]) / n * 100, 3),
            "small_delta_suppressed": not safe,
        }
        if safe:
            entry.update(deltas)
        summary[window] = entry

    return {
        "stage": "STEP31_EXPANDED_IMAGING_AGGREGATE_RECONCILIATION",
        "all_aggregate_checks_passed": True,
        "patient_level_rows_read": 0,
        "original_source_rows_read": 0,
        "study_population": "2018-2019 first observed principal I63 diagnosis, approximate ages 19-50",
        "study_cohort_n": n,
        "per_window": summary,
        "main_findings": [
            "Adding five head/neck CPT codes increases vascular recorded-code matches.",
            "Additional codes make only a small change to the size of the no-matched-code group.",
            "Absence of a matched CPT does not establish that imaging was not performed.",
            "Neither admission-level attribution nor population imaging utilization is established."
        ],
        "clinical_inference_approved": False,
        "race_ethnicity_disparity_modeling_approved": False,
        "cross_report_disclosure_review_required": True,
        "research_decision": (
            "Pause clinical disparity inference; investigate source code capture and "
            "consider an imaging-cohort-selection/methodological paper before models."
        )
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--preflight", type=Path, required=True)
    p.add_argument("--expanded", type=Path, required=True)
    p.add_argument("--legacy-step22", type=Path, required=True)
    p.add_argument("--output", type=Path,
                   default=Path("results/phase1/step31_expanded_reconciliation.json"))
    args = p.parse_args()
    source = [json.loads(path.read_text(encoding="utf-8"))
              for path in (args.preflight, args.expanded, args.legacy_step22)]
    result = reconcile(*source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("Step 31 aggregate reconciliation passed:", args.output)
    print("Source rows read: 0. No clinical inference authorization implied.")


if __name__ == "__main__":
    main()
