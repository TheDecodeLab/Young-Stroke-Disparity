"""Step 11: audit diagnosis-to-procedure linkage in the pre-exclusion file.

PROVENANCE AUDIT ONLY: diagnosis dates are not encounter identifiers, and
the source contains only diagnoses already linked to imaging. No patient IDs,
individual dates or rows are ever included in the aggregate JSON output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ("CT", "MRI", "CTA", "MRA")
EVENT_COLS = ("patient_id", "datetime_dx", "datetime_px", "category",
              "Stroke", "principal_diagnosis_indicator", "CPTcode")


def audit_events(events: pd.DataFrame, candidate: pd.DataFrame | None = None,
                 legacy: pd.DataFrame | None = None) -> dict:
    """Audit earliest imaging-linked diagnosis and repeated event mapping."""
    if missing := set(EVENT_COLS) - set(events.columns):
        raise ValueError(f"Missing pre-exclusion event fields: {sorted(missing)}")
    e = events[list(EVENT_COLS)].copy()
    if e.patient_id.isna().any():
        raise ValueError("Missing patient IDs in event file; inspect upstream")
    for date_col in ("datetime_dx", "datetime_px"):
        e[date_col] = pd.to_datetime(e[date_col], errors="coerce")
    bad = int(e[["datetime_dx", "datetime_px"]].isna().any(axis=1).sum())
    if bad:
        raise ValueError(f"{bad} event rows have unparseable diagnosis/procedure dates")
    e["category"] = e["category"].astype("string").str.strip().str.upper()
    if unknown := int((~e["category"].isin(CATEGORIES)).sum()):
        raise ValueError(f"{unknown} rows have unknown procedure categories")

    days = (e.datetime_px - e.datetime_dx).dt.days
    lag_invalid = int(days.abs().gt(7).sum())
    principal = e["principal_diagnosis_indicator"].astype("string").str.strip().str.upper().eq("P")
    ischemic = e["Stroke"].astype("string").str.strip().str.lower().eq("ischemic")
    selected = e.loc[principal & ischemic].copy()
    if selected.empty:
        raise ValueError("No principal ischemic stroke records in intermediate")

    # A procedure may link to different diagnoses because the old join
    # originally used patient_id rather than a true encounter identifier.
    links = selected.groupby(
        ["patient_id", "datetime_px", "CPTcode"], dropna=False,
    )["datetime_dx"].nunique()
    repeated_keys = int(links.gt(1).sum())

    # Provisional patient + diagnosis-date flags (not admissions).
    x = selected[["patient_id", "datetime_dx", "category"]].drop_duplicates()
    x["present"] = 1
    wide = x.pivot_table(index=["patient_id", "datetime_dx"], columns="category",
                         values="present", fill_value=0, aggfunc="max")
    for c in CATEGORIES:
        if c not in wide:
            wide[c] = 0
    wide = wide[list(CATEGORIES)].reset_index()
    for c in CATEGORIES:
        wide[c] = wide[c].astype("int8")
    wide["advanced"] = wide[["MRI", "CTA", "MRA"]].any(axis=1)
    dates_per_patient = wide.groupby("patient_id").size()
    first = wide.sort_values(["patient_id", "datetime_dx"]).drop_duplicates(
        "patient_id", keep="first",
    ).copy().set_index("patient_id", drop=False)
    assert first.index.is_unique

    any_flags = wide.groupby("patient_id")[list(CATEGORIES)].max()
    any_advanced = any_flags[["MRI", "CTA", "MRA"]].any(axis=1)
    first_ct = first.CT.eq(1)
    first_adv = first.advanced
    first_ct_only = first_ct & ~first_adv
    first_adv_only = ~first_ct & first_adv
    report = {
        "source_event_rows": int(len(e)),
        "principal_ischemic_event_rows": int(len(selected)),
        "out_of_7_day_window_rows": lag_invalid,
        "repeated_procedure_link_keys": repeated_keys,
        "repeated_procedure_link_diagnosis_rows": int(links[links.gt(1)].sum()),
        "unique_patients_with_linked_ischemic_diagnoses": int(len(first)),
        "unique_patient_diagnosis_dates": int(len(wide)),
        "patients_with_multiple_linked_diagnosis_dates": int(dates_per_patient.gt(1).sum()),
        "earliest_linked_diagnosis": {
            "ct_and_advanced_n": int((first_ct & first_adv).sum()),
            "ct_only_n": int(first_ct_only.sum()),
            "advanced_without_ct_n": int(first_adv_only.sum()),
            "any_ct_n": int(first_ct.sum()),
        },
        "patients_ct_only_at_earliest_but_advanced_at_another_linked_diagnosis_n":
            int((first_ct_only & any_advanced).sum()),
        "patients_advanced_without_ct_at_earliest_but_ct_at_another_linked_diagnosis_n":
            int((first_adv_only & any_flags.CT.eq(1)).sum()),
        "status": "AUDIT_ONLY_NOT_A_VALIDATED_INDEX_COHORT",
        "caveats": [
            "Earliest imaging-linked diagnosis need not be first principal stroke diagnosis.",
            "Diagnosis dates are not encounter/admission identifiers.",
            "Historical patient-only join may link a procedure to multiple diagnoses.",
            "Do not use these provisional counts for manuscript inference.",
        ],
    }
    for label, data in (("candidate", candidate), ("legacy", legacy)):
        if data is None:
            continue
        if missing := {"patient_id", "dx_year", "MRI", "CTA", "MRA"} - set(data):
            raise ValueError(f"{label} missing columns: {sorted(missing)}")
        if data.patient_id.isna().any() or data.patient_id.duplicated().any():
            raise ValueError(f"{label} patient IDs must be unique and complete")
        d = data.set_index("patient_id")
        shared = first.index.intersection(d.index)
        one, two = first.loc[shared], d.loc[shared]
        dy = pd.to_numeric(two["dx_year"], errors="coerce")
        if dy.isna().any():
            raise ValueError(f"{label} has invalid diagnosis years")
        compare = {
            "saved_rows": int(len(data)),
            "linked_in_pre_exclusion_file_n": int(len(shared)),
            "not_linked_in_pre_exclusion_file_n": int(len(data) - len(shared)),
            "earliest_linked_dx_year_differs_from_saved_year_n":
                int(one.datetime_dx.dt.year.ne(dy).sum()),
            "earliest_linked_diagnosis_ct_only_n":
                int((one.CT.eq(1) & ~one.advanced).sum()),
            "earliest_linked_diagnosis_advanced_without_ct_n":
                int((one.CT.eq(0) & one.advanced).sum()),
        }
        for modality in ("MRI", "CTA", "MRA"):
            counts = pd.to_numeric(two[modality], errors="coerce")
            if counts.isna().any() or counts.lt(0).any():
                raise ValueError(f"{label}: invalid {modality} counts")
            compare[f"earliest_linked_{modality.lower()}_receipt_differs_from_saved_n"] = (
                int(one[modality].eq(1).ne(counts.gt(0)).sum())
            )
        report[f"{label}_comparison"] = compare
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, default=ROOT.parent / "df_merged_age.parquet")
    parser.add_argument("--candidate", type=Path,
                        default=ROOT.parent / "df_trinetx_total_young_wCT.parquet")
    parser.add_argument("--legacy", type=Path,
                        default=ROOT.parent / "df_trinetx_total_young.parquet")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/phase1/event_linkage_audit.json")
    args = parser.parse_args()
    events = pd.read_parquet(args.events, columns=list(EVENT_COLS))
    cols = ["patient_id", "dx_year", "MRI", "CTA", "MRA"]
    candidate = pd.read_parquet(args.candidate, columns=cols)
    legacy = pd.read_parquet(args.legacy, columns=cols)
    report = audit_events(events, candidate, legacy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Saved aggregate report to {args.output}")
    print("Patients with multiple linked diagnosis dates:",
          report["patients_with_multiple_linked_diagnosis_dates"])
    print("One procedure linked to multiple diagnoses (keys):",
          report["repeated_procedure_link_keys"])
    print("STOP: event-linkage audit is not an index-stroke cohort reconstruction")


if __name__ == "__main__":
    main()
