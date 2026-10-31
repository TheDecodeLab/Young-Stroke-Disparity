"""Step 12: diagnostic comparison of imaging-linked index definitions.

This is NOT a validated index-stroke cohort. The input is conditioned on
diagnoses already linked to imaging, without confirmed encounter IDs.
Compare first imaging-linked, first CT-linked and first advanced-linked
diagnoses among people with CT at some linked diagnosis.
Only aggregate counts are saved, never patient identifiers or rows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODALITIES = ("CT", "MRI", "CTA", "MRA")
REQUIRED = {"patient_id", "datetime_dx", "datetime_px", "category",
            "Stroke", "principal_diagnosis_indicator"}


def summarize(df: pd.DataFrame) -> dict:
    """Quantify the effect of index definition on imaging receipt.

    Diagnosis dates are provisional event keys, not hospital admissions.
    """
    if missing := REQUIRED - set(df):
        raise ValueError(f"Missing event columns: {sorted(missing)}")
    if df["patient_id"].isna().any():
        raise ValueError("Patient identifiers are missing in intermediate")
    d = df[list(REQUIRED)].copy()
    for date in ("datetime_dx", "datetime_px"):
        d[date] = pd.to_datetime(d[date], errors="coerce")
        if d[date].isna().any():
            raise ValueError(f"Invalid {date}")
    d["category"] = d["category"].astype("string").str.strip().str.upper()
    if not d["category"].isin(MODALITIES).all():
        raise ValueError("Unexpected imaging category")
    d = d[
        d["Stroke"].astype("string").str.strip().str.lower().eq("ischemic")
        & d["principal_diagnosis_indicator"].astype("string").str.upper().eq("P")
    ].copy()
    if d.empty:
        raise ValueError("No principal ischemic stroke imaging-linked events")
    if (d["datetime_px"] - d["datetime_dx"]).abs().gt(pd.Timedelta(days=7)).any():
        raise ValueError("Input contains events outside +/-7 days")

    # Receipt rather than procedure counts: upstream patient-only joins
    # and deduplication can distort multiplicity of procedure events.
    d = d[["patient_id", "datetime_dx", "category"]].drop_duplicates()
    d["observed"] = 1
    wide = d.pivot_table(index=["patient_id", "datetime_dx"],
                         columns="category", values="observed",
                         aggfunc="max", fill_value=0)
    for name in MODALITIES:
        if name not in wide:
            wide[name] = 0
    wide = wide[list(MODALITIES)].reset_index()
    wide["has_advanced"] = wide[["MRI", "CTA", "MRA"]].gt(0).any(axis=1)
    wide = wide.sort_values(["patient_id", "datetime_dx"])

    first_any = wide.drop_duplicates("patient_id").set_index("patient_id")
    first_ct = wide[wide["CT"].eq(1)].drop_duplicates("patient_id").set_index("patient_id")
    ct_ever = first_ct.index
    first_advanced_given_ct = (
        wide[wide["patient_id"].isin(ct_ever) & wide["has_advanced"]]
        .drop_duplicates("patient_id").set_index("patient_id")
    )
    shared = first_ct.index.intersection(first_advanced_given_ct.index)
    ct, advanced = first_ct.loc[shared], first_advanced_given_ct.loc[shared]
    different_dates = ct["datetime_dx"].ne(advanced["datetime_dx"])
    interval = (advanced["datetime_dx"] - ct["datetime_dx"]).dt.days

    first_any_with_ct_ever = first_any.loc[ct_ever]
    report = {
        "status": "DIAGNOSTIC_ONLY_NO_INFERENCE",
        "linked_principal_ischemic_event_rows_deduplicated": int(len(d)),
        "linked_patient_diagnosis_dates": int(len(wide)),
        "linked_patients_any_imaging": int(len(first_any)),
        "patients_with_ct_at_any_linked_diagnosis": int(len(first_ct)),
        "patients_with_ct_and_advanced_at_any_diagnoses": int(len(first_advanced_given_ct)),
        "patients_ct_without_advanced_at_any_linked_diagnosis": int(
            len(first_ct) - len(first_advanced_given_ct)),
        "first_ct_linked_diagnosis": {
            "ct_only_n": int((~first_ct["has_advanced"]).sum()),
            "ct_and_advanced_n": int(first_ct["has_advanced"].sum()),
        },
        "first_any_linked_diagnosis_among_ct_ever": {
            "ct_present_n": int(first_any_with_ct_ever["CT"].sum()),
            "advanced_without_ct_n": int(
                (first_any_with_ct_ever["CT"].eq(0) & first_any_with_ct_ever["has_advanced"]).sum()),
            "date_differs_from_first_ct_n": int(
                first_any_with_ct_ever["datetime_dx"].ne(first_ct["datetime_dx"]).sum()),
        },
        "first_advanced_vs_first_ct_among_patients_with_both_anywhere": {
            "n": int(len(shared)),
            "same_linked_diagnosis_date_n": int((~different_dates).sum()),
            "different_linked_diagnosis_date_n": int(different_dates.sum()),
            "first_advanced_before_first_ct_n": int(interval.lt(0).sum()),
            "first_advanced_after_first_ct_n": int(interval.gt(0).sum()),
            "first_advanced_different_diagnosis_year_n": int(
                ct["datetime_dx"].dt.year.ne(advanced["datetime_dx"].dt.year).sum()),
        },
        "caveats": [
            "Only imaging-linked diagnoses exist in this intermediate; earlier strokes may be omitted.",
            "CT and advanced imaging may be linked by patient, not by encounter.",
            "Upstream duplicate removal masks some ambiguous procedure-to-diagnosis links.",
            "Do not use this audit to derive publication imaging rates or adjusted associations.",
        ],
    }
    ct_total = report["patients_with_ct_at_any_linked_diagnosis"]
    assert ct_total == (report["first_ct_linked_diagnosis"]["ct_only_n"]
                        + report["first_ct_linked_diagnosis"]["ct_and_advanced_n"])
    assert report["first_advanced_vs_first_ct_among_patients_with_both_anywhere"]["n"] == (
        ct_total - report["patients_ct_without_advanced_at_any_linked_diagnosis"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, default=ROOT.parent / "df_merged_age.parquet")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/phase1/index_definition_audit.json")
    args = parser.parse_args()
    data = pd.read_parquet(args.events, columns=sorted(REQUIRED))
    summary = summarize(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("Aggregate audit:", args.output)
    print("CT-linked patients:", summary["patients_with_ct_at_any_linked_diagnosis"])
    print("CT-only at first CT-linked diagnosis:",
          summary["first_ct_linked_diagnosis"]["ct_only_n"])
    print("CAUTION: provisional event dates, not verified stroke admissions.")


if __name__ == "__main__":
    main()
