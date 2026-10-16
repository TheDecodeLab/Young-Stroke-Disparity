"""Step 5: audit selection due to missing race and ethnicity.

Generate aggregate-only missingness comparisons from a derived local cohort.
This is a diagnostic for possible selection bias, NOT an imputation method
and NOT an estimate of racial inequity or the missingness mechanism.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTCOMES = ("MRI_received", "vascular_received")


def summarize_missingness(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize known/unknown demographic values by sex and index year.

    All rows count individuals, not imaging procedures. Small cells are
    suppressed below the threshold to reduce disclosure risk.
    """
    required = {"race", "ethnicity", "sex", "dx_year", *OUTCOMES}
    if missing := required - set(df.columns):
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    for y in OUTCOMES:
        if df[y].isna().any() or not df[y].isin([0, 1]).all():
            raise ValueError(f"{y} must be complete and binary")
    if df["sex"].isna().any() or df["dx_year"].isna().any():
        raise ValueError("Missing sex or index year: inspect cohort preparation")
    result = []
    for demographic in ("race", "ethnicity"):
        known = df[demographic].notna()
        for dimension in ("overall", "sex", "dx_year"):
            strata = pd.Series("All", index=df.index) if dimension == "overall" else df[dimension]
            for (group, available), part in df.groupby([strata, known], dropna=False):
                n = int(len(part))
                result.append({
                    "demographic": demographic,
                    "stratified_by": dimension,
                    "group": str(group),
                    "availability": "Known" if available else "Missing/unknown",
                    "n": n,
                    "MRI_received_n": int(part["MRI_received"].sum()),
                    "MRI_received_pct": round(100 * float(part["MRI_received"].mean()), 2),
                    "vascular_received_n": int(part["vascular_received"].sum()),
                    "vascular_received_pct": round(100 * float(part["vascular_received"].mean()), 2),
                })
    return pd.DataFrame(result).sort_values(
        ["demographic", "stratified_by", "group", "availability"]
    ).reset_index(drop=True)


def suppress_small_cells(table: pd.DataFrame, threshold: int = 11) -> pd.DataFrame:
    """Suppress all numerical cells for strata smaller than threshold.

    Applied to *output only*. Complementary suppression is not guaranteed;
    thus do not publicly disclose the table without a disclosure-control
    review, especially when overlapping breakdowns can reveal small cells.
    """
    if threshold < 1:
        raise ValueError("threshold must be at least 1")
    out = table.copy()
    mask = out["n"] < threshold
    for col in ("n", "MRI_received_n", "MRI_received_pct",
                "vascular_received_n", "vascular_received_pct"):
        out.loc[mask, col] = pd.NA
    out["suppressed_small_cell"] = mask
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "results/phase1/cohort_age50.parquet")
    parser.add_argument("--output", type=Path, default=ROOT / "results/phase1/missingness_age50.csv")
    args = parser.parse_args()
    df = pd.read_parquet(args.input)
    summary = suppress_small_cells(summarize_missingness(df))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output, index=False)
    print(f"Missingness audit saved locally: {args.output}")
    print("STOP: race/ethnicity missingness remains substantial. No adjusted clinical models are validated.")


if __name__ == "__main__":
    main()
