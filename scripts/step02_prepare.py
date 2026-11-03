"""Step 2: derive a clearly defined, patient-level analytic cohort locally.

The original dataset was *already restricted* at <=52 (men) / <=54 (women).
Only common age caps <=52 are supported. A <=55 sensitivity analysis needs
new source extraction. Never treat this file as an unrestricted source cohort.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ["neither", "CTA only", "MRA only", "both"]


def prepare(df: pd.DataFrame, max_age: int = 50) -> pd.DataFrame:
    if not 19 <= max_age <= 52:
        raise ValueError("Only 19-52 common upper-age cutoffs can be reconstructed from this sex-restricted source.")
    needed = ["patient_id", "sex", "race", "ethnicity", "age@stroke", "dx_year", "stroke", "MRI", "CTA", "MRA"]
    if any(x not in df.columns for x in needed):
        raise ValueError(f"Missing columns: {sorted(set(needed) - set(df.columns))}")
    if df["patient_id"].isna().any() or df["patient_id"].duplicated().any():
        raise ValueError("Expected exactly one record per patient. Resolve duplication first.")
    data = df.copy()
    data["sex"] = data["sex"].astype("string").str.strip().str.lower().map(
        {"men": "Men", "male": "Men", "m": "Men", "women": "Women", "female": "Women", "f": "Women"}
    )
    if data["sex"].isna().any():
        raise ValueError("Unknown sex codes: do not silently assign an exposure category.")
    data["age_at_stroke"] = pd.to_numeric(data["age@stroke"], errors="coerce")
    data = data[data["stroke"].astype(str).str.lower().eq("ischemic") &
                data["age_at_stroke"].gt(18) & data["age_at_stroke"].le(max_age)].copy()
    for col in ("MRI", "CTA", "MRA"):
        values = pd.to_numeric(data[col], errors="coerce")
        if values.isna().any() or (~np.isfinite(values)).any() or (values < 0).any() or (values % 1 != 0).any():
            raise ValueError(f"Invalid imaging counts in {col}; correct source data.")
        data[f"{col}_count"] = values.astype("int64")
        data[f"{col}_received"] = (values > 0).astype("int8")
    data["vascular_received"] = ((data["CTA_received"] == 1) | (data["MRA_received"] == 1)).astype("int8")
    data["total_imaging_count"] = data[["MRI_count", "CTA_count", "MRA_count"]].sum(axis=1)
    vascular_choice = np.select(
        [(data["CTA_received"] == 1) & (data["MRA_received"] == 1),
         data["CTA_received"] == 1, data["MRA_received"] == 1],
        ["both", "CTA only", "MRA only"], default="neither"
    )
    data["vascular_pattern"] = pd.Categorical(vascular_choice, categories=CATEGORIES)
    for col in ("race", "ethnicity"):
        data[col] = data[col].astype("string").str.strip().replace(
            {"Unknown": pd.NA, "XXX": pd.NA, "": pd.NA}
        )
    # Explicitly exclude patient_id, postal_code, and sex-containing CHA2DS2-VASc.
    return data[["sex", "race", "ethnicity", "age_at_stroke", "dx_year",
                 "MRI_count", "CTA_count", "MRA_count",
                 "MRI_received", "CTA_received", "MRA_received", "vascular_received",
                 "vascular_pattern", "total_imaging_count"]].reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "dataset/df_trinetx_total_young.parquet")
    parser.add_argument("--max-age", type=int, default=50)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    target = args.output or ROOT / f"results/phase1/cohort_age{args.max_age}.parquet"
    result = prepare(pd.read_parquet(args.input), max_age=args.max_age)
    target.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(target, index=False)
    print(f"Prepared {len(result)} records for ages 19-{args.max_age}. Local output: {target}")
    print("No inference about clinical adequacy is possible from imaging counts alone.")


if __name__ == "__main__":
    main()
