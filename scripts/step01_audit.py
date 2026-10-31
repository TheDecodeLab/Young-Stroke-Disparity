"""Step 1: audit existing TriNetX analysis table without exporting patient records.

This audits the *derived* parquet table, not the source diagnosis/procedure tables.
The source-level CT requirement, principal diagnosis, and imaging time windows
cannot be independently verified from this file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "patient_id", "sex", "race", "ethnicity", "age@stroke", "dx_year",
    "stroke", "MRI", "CTA", "MRA",
}
UNKNOWN = {"", "unknown", "xxx", "nan", "none", "null"}


def unknown_mask(series: pd.Series) -> pd.Series:
    """Flag genuine nulls plus TriNetX's string-coded unknown categories."""
    return series.isna() | series.astype("string").str.strip().str.lower().isin(UNKNOWN).fillna(False)


def audit_frame(df: pd.DataFrame) -> dict:
    """Return aggregate-only diagnostics. No patient IDs or example rows."""
    missing_cols = sorted(REQUIRED - set(df.columns))
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    report = {
        "rows": int(len(df)),
        "distinct_patient_ids": int(df["patient_id"].nunique(dropna=True)),
        "duplicate_patient_ids": int(df["patient_id"].duplicated().sum()),
        "columns": sorted(map(str, df.columns)),
        "missing_or_unknown": {},
        "modality_counts": {},
        "warnings": [],
    }
    for col in ("sex", "race", "ethnicity", "age@stroke", "dx_year", "stroke"):
        mask = unknown_mask(df[col]) if col in ("sex", "race", "ethnicity") else df[col].isna()
        report["missing_or_unknown"][col] = {
            "n": int(mask.sum()),
            "fraction": round(float(mask.mean()), 6) if len(df) else None,
        }
    for col in ("MRI", "CTA", "MRA"):
        numeric = pd.to_numeric(df[col], errors="coerce")
        invalid = numeric.isna() | (~np.isfinite(numeric)) | (numeric < 0) | (numeric % 1 != 0)
        report["modality_counts"][col] = {
            "invalid_n": int(invalid.sum()),
            "zero_n": int(numeric.eq(0).sum()),
            "positive_n": int(numeric.gt(0).sum()),
            "count_max": float(numeric.max()) if numeric.notna().any() else None,
        }
        if invalid.any():
            report["warnings"].append(f"{col}: invalid/noninteger procedure counts detected.")
    age = pd.to_numeric(df["age@stroke"], errors="coerce")
    sex = df["sex"].astype("string").str.lower().str.strip()
    report["age_summary"] = {
        "min": float(age.min()) if age.notna().any() else None,
        "max": float(age.max()) if age.notna().any() else None,
        "age_le_18_n": int(age.le(18).sum()),
        "over_prior_sex_threshold_n": int(
            ((sex.isin(["men", "male", "m"])) & age.gt(52) |
             (sex.isin(["women", "female", "f"])) & age.gt(54)).sum()
        ),
    }
    report["stroke_values"] = sorted(df["stroke"].dropna().astype(str).unique().tolist())
    report["years"] = sorted(df["dx_year"].dropna().astype(str).unique().tolist())
    if report["duplicate_patient_ids"]:
        report["warnings"].append("Patient IDs repeat; investigate records across years before modeling.")
    if report["missing_or_unknown"]["race"]["fraction"] is not None and report["missing_or_unknown"]["race"]["fraction"] > .5:
        report["warnings"].append("Race missing/unknown exceeds 50%; race models need a selection-bias audit.")
    if "CHA2DS2_VASc_score" in df:
        report["warnings"].append("Existing CHA2DS2-VASc includes sex; do NOT reuse as a sex-model adjustment.")
    if "postal_code" in df or "patient_id" in df:
        report["warnings"].append("Patient-level identifiers/geography exist in source; check public repository permissions.")
    report["warnings"].append("Derived table cannot verify eligibility, CPT mapping, or +/-7-day timing.")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "dataset/df_trinetx_total_young.parquet")
    parser.add_argument("--output", type=Path, default=ROOT / "results/phase1/trinetx_audit.json")
    args = parser.parse_args()
    report = audit_frame(pd.read_parquet(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Audited {report['rows']} records; {len(report['warnings'])} audit warnings.")
    print(f"Aggregate report: {args.output}")
    if any(v["invalid_n"] for v in report["modality_counts"].values()) or report["duplicate_patient_ids"]:
        raise SystemExit("Audit failed: invalid counts or duplicated IDs. Review report before proceeding.")


if __name__ == "__main__":
    main()
