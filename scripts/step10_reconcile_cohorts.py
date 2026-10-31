"""Step 10: reconcile the CT-retaining and legacy young-stroke tables.

Runs locally, writes only aggregate counts and reproducibility diagnostics.
Never uploads, prints or exports patient identifiers or individual records.

This is a candidate-table comparison, NOT a validated stroke cohort.
A missing patient in one table may reflect different extraction versions,
age/first-event rules, procedure linkage, or eligibility.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODALITIES = ("MRI", "CTA", "MRA")
CANDIDATE_COLUMNS = ("patient_id", "CT", *MODALITIES, "sex", "age@stroke", "dx_year", "stroke")
LEGACY_COLUMNS = ("patient_id", *MODALITIES, "sex", "age@stroke", "dx_year", "stroke")


def validate(df: pd.DataFrame, name: str, has_ct: bool) -> pd.DataFrame:
    """Validate required values without silently imputing zeroes."""
    required = CANDIDATE_COLUMNS if has_ct else LEGACY_COLUMNS
    if missing := set(required) - set(df.columns):
        raise ValueError(f"{name}: missing columns {sorted(missing)}")
    if df["patient_id"].isna().any() or df["patient_id"].duplicated().any():
        raise ValueError(f"{name}: missing or duplicated patient identifiers")
    d = df[list(required)].copy()
    for col in (*MODALITIES, *(("CT",) if has_ct else ())):
        raw = pd.to_numeric(d[col], errors="coerce")
        invalid = raw.isna() | (~np.isfinite(raw)) | raw.lt(0) | raw.mod(1).ne(0)
        if invalid.any():
            raise ValueError(f"{name}: invalid procedure counts for {col}")
        d[col] = raw.astype("int64")
    d["age@stroke"] = pd.to_numeric(d["age@stroke"], errors="coerce")
    if d["age@stroke"].isna().any() or (~np.isfinite(d["age@stroke"])).any():
        raise ValueError(f"{name}: missing/invalid age")
    sex = d["sex"].astype("string").str.lower().str.strip()
    d["sex"] = sex.map({
        "m": "Men", "male": "Men", "men": "Men",
        "f": "Women", "female": "Women", "women": "Women",
    })
    if d["sex"].isna().any():
        raise ValueError(f"{name}: unknown sex codes")
    return d


def categorize(df: pd.DataFrame) -> pd.DataFrame:
    """Mark imaging receipt without collapsing procedure counts into a rate."""
    result = df.copy()
    result["any_advanced"] = result[list(MODALITIES)].gt(0).any(axis=1)
    if "CT" in result:
        result["has_ct"] = result["CT"].gt(0)
        result["ct_only"] = result["has_ct"] & ~result["any_advanced"]
        result["ct_plus_advanced"] = result["has_ct"] & result["any_advanced"]
        result["advanced_without_ct"] = ~result["has_ct"] & result["any_advanced"]
    return result


def group_counts(d: pd.DataFrame) -> dict[str, Any]:
    """Compute only large overall and age-band aggregates."""
    out: dict[str, Any] = {"patients_n": int(len(d))}
    if "CT" in d:
        for flag in ("has_ct", "ct_only", "ct_plus_advanced", "advanced_without_ct"):
            out[f"{flag}_n"] = int(d[flag].sum())
    out["any_advanced_n"] = int(d["any_advanced"].sum())
    out["without_advanced_n"] = int((~d["any_advanced"]).sum())
    out["no_ct_no_advanced_n"] = int(
        ((~d["has_ct"]) & (~d["any_advanced"])).sum()
    ) if "CT" in d else None
    out["sex_counts"] = {str(k): int(v) for k, v in d["sex"].value_counts().items()}
    out["age_min"] = float(d["age@stroke"].min()) if len(d) else None
    out["age_max"] = float(d["age@stroke"].max()) if len(d) else None
    return out


def reconcile(candidate: pd.DataFrame, legacy: pd.DataFrame) -> dict[str, Any]:
    """Compare patient membership, coding and image counts across files."""
    a = categorize(validate(candidate, "candidate", True))
    b = categorize(validate(legacy, "legacy", False))

    def eligible(df: pd.DataFrame, max_age: int) -> pd.DataFrame:
        age_ok = df["age@stroke"].gt(18) & df["age@stroke"].le(max_age)
        stroke_ok = df["stroke"].astype("string").str.lower().str.strip().eq("ischemic")
        return df.loc[age_ok & stroke_ok]

    all_a = set(a["patient_id"])
    all_b = set(b["patient_id"])
    shared = all_a & all_b
    matched = a.merge(b, on="patient_id", how="inner", suffixes=("_candidate", "_legacy"),
                      validate="one_to_one")
    consistency = {}
    for field in ("MRI", "CTA", "MRA", "sex", "age@stroke", "dx_year", "stroke"):
        consistency[field] = {
            "mismatch_n": int((matched[f"{field}_candidate"].astype("string")
                               != matched[f"{field}_legacy"].astype("string")).fillna(True).sum())
        }
    consistency["legacy_patient_ids_with_no_ct_candidate_n"] = int(
        (~matched["has_ct"]).sum()
    )
    consistency["legacy_patient_ids_with_ct_only_candidate_n"] = int(
        matched["ct_only"].sum()
    )
    consistency["shared_patients_with_any_advanced_mismatch_n"] = int(
        (matched["any_advanced_candidate"] != matched["any_advanced_legacy"]).sum()
    )

    sections = {}
    for label, cap in (("as_saved", None), ("age19_to_45", 45), ("age19_to_50", 50)):
        ca = a if cap is None else eligible(a, cap)
        le = b if cap is None else eligible(b, cap)
        ca_ids, le_ids = set(ca["patient_id"]), set(le["patient_id"])
        sections[label] = {
            "candidate": group_counts(ca),
            "legacy": group_counts(le),
            "overlap_n": len(ca_ids & le_ids),
            "candidate_only_n": len(ca_ids - le_ids),
            "legacy_only_n": len(le_ids - ca_ids),
            "candidate_ct_positive_and_advanced_n": int(ca["ct_plus_advanced"].sum()),
            "difference_legacy_vs_candidate_ct_plus_advanced_n":
                int(len(le) - int(ca["ct_plus_advanced"].sum())),
        }
    return {
        "source_files": "candidate CT-inclusive derived vs legacy advanced-imaging-derived",
        "as_saved_intersection_n": len(shared),
        "as_saved_candidate_only_n": len(all_a - all_b),
        "as_saved_legacy_only_n": len(all_b - all_a),
        "matched_patient_fields": consistency,
        "cohort_summaries": sections,
        "status": "BLOCKED_FOR_INFERENCE",
        "warnings": [
            "A CT positive flag in a derived table does not confirm correct stroke encounter timing.",
            "Shared IDs and imaging count differences must be resolved before any revised estimates.",
            "An age <=55 cohort cannot be recovered from a source already sex-restricted at <=52/54.",
            "This reconciliation is not a re-analysis and must not be used for manuscript results.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=ROOT.parent / "df_trinetx_total_young_wCT.parquet")
    parser.add_argument("--legacy", type=Path, default=ROOT.parent / "df_trinetx_total_young.parquet")
    parser.add_argument("--output", type=Path, default=ROOT / "results/phase1/cohort_reconciliation.json")
    args = parser.parse_args()
    ca = pd.read_parquet(args.candidate, columns=list(CANDIDATE_COLUMNS))
    le = pd.read_parquet(args.legacy, columns=list(LEGACY_COLUMNS))
    report = reconcile(ca, le)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Saved aggregate comparison: {args.output}")
    for label, sec in report["cohort_summaries"].items():
        print(f"{label}: CT-only {sec['candidate'].get('ct_only_n')}; "
              f"candidate CT+advanced {sec['candidate_ct_positive_and_advanced_n']}; "
              f"legacy {sec['legacy']['patients_n']}; "
              f"overlap {sec['overlap_n']}")
    print("STOP: reconcile index diagnoses and imaging event timing before refitting models.")


if __name__ == "__main__":
    main()
