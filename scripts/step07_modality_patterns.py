"""Step 7: descriptive, mutually exclusive vascular imaging pathways.

Uses the age-restricted, derived analysis cohort, not original CPT/index
event records. Categories indicate recorded receipt, not clinical indication,
sequence, substitution, or appropriateness. Output is aggregate only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ("neither", "CTA only", "MRA only", "both")
REQUIRED = {
    "age_at_stroke", "dx_year", "sex", "MRI_received", "CTA_received",
    "MRA_received", "vascular_received", "vascular_pattern",
}


def validate_cohort(df: pd.DataFrame) -> None:
    """Fail rather than silently repair inconsistent imaging definitions."""
    missing = sorted(REQUIRED - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if df.empty:
        raise ValueError("The analytic cohort is empty")
    if df[list(REQUIRED)].isna().any().any():
        raise ValueError("The prepared analysis variables must be complete")
    if not df["sex"].isin(["Men", "Women"]).all():
        raise ValueError("Unexpected sex category")
    for col in ("MRI_received", "CTA_received", "MRA_received", "vascular_received"):
        if not df[col].isin([0, 1]).all():
            raise ValueError(f"{col} must contain only 0/1")
    expect_any = df["CTA_received"].eq(1) | df["MRA_received"].eq(1)
    if not expect_any.eq(df["vascular_received"].eq(1)).all():
        raise ValueError("Vascular receipt is inconsistent with CTA and MRA")
    expected = np.select(
        [df["CTA_received"].eq(1) & df["MRA_received"].eq(1),
         df["CTA_received"].eq(1), df["MRA_received"].eq(1)],
        ["both", "CTA only", "MRA only"], default="neither",
    )
    if not np.all(expected == df["vascular_pattern"].astype(str).to_numpy()):
        raise ValueError("Vascular pattern labels disagree with recorded receipt")
    age = pd.to_numeric(df["age_at_stroke"], errors="coerce")
    if age.isna().any() or not age.between(19, 50).all():
        raise ValueError("This summary is defined for age 19-50 only")


def summarize_modality_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Count four patterns and MRI receipt within each pattern.

    Overlapping aggregate strata may still require disclosure control.
    Keep CSVs local until institutional authorization is verified.
    """
    validate_cohort(df)
    frames = []
    bands = pd.cut(
        df["age_at_stroke"], bins=[18, 29, 39, 50],
        labels=["19-29", "30-39", "40-50"], include_lowest=True,
    ).astype(str)
    specs = [
        ("overall", pd.Series("All", index=df.index)),
        ("sex", df["sex"].astype(str)),
        ("year", df["dx_year"].astype(str)),
        ("age_band", bands),
        ("sex_x_year", df["sex"].astype(str) + " | " + df["dx_year"].astype(str)),
        ("sex_x_age_band", df["sex"].astype(str) + " | " + bands),
    ]
    patterns = df["vascular_pattern"].astype(str)
    for stratification, groups in specs:
        for label, part in df.groupby(groups, sort=True):
            n = len(part)
            pattern = patterns.loc[part.index]
            for p in PATTERNS:
                mask = pattern.eq(p)
                c = int(mask.sum())
                mri_n = int(part.loc[mask, "MRI_received"].sum())
                frames.append({
                    "stratification": stratification, "group": str(label),
                    "pattern": p, "group_n": int(n), "pattern_n": c,
                    "pattern_pct": 100 * c / n,
                    "MRI_within_pattern_n": mri_n,
                    "MRI_within_pattern_pct": 100 * mri_n / c if c else np.nan,
                })
    summary = pd.DataFrame(frames)
    totals = summary.groupby(["stratification", "group"], sort=False)["pattern_n"].sum()
    sizes = summary.groupby(["stratification", "group"], sort=False)["group_n"].first()
    if not totals.eq(sizes).all():
        raise AssertionError("Vascular patterns do not partition every stratum")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "results/phase1/cohort_age50.parquet")
    parser.add_argument("--output", type=Path, default=ROOT / "results/phase1/modality_patterns_age50.csv")
    args = parser.parse_args()
    result = summarize_modality_patterns(pd.read_parquet(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"Saved {len(result)} aggregate rows to local file: {args.output}")
    print("Descriptive only; cannot establish indication, substitution or appropriateness.")


if __name__ == "__main__":
    main()
