"""Step 3: report denominators and imaging receipt (not counts as probabilities).

All output is aggregate. These are descriptive data, not disparity or causal
estimates. Do not automatically push results to a public GitHub repository.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTCOMES = ["MRI_received", "CTA_received", "MRA_received", "vascular_received"]


def describe(df: pd.DataFrame) -> pd.DataFrame:
    required = {"sex", "race", "ethnicity", "vascular_pattern", *OUTCOMES}
    if missing := required - set(df.columns):
        raise ValueError(f"Missing analytic columns: {sorted(missing)}")
    frames = []
    for stratifier in ["sex", "race", "ethnicity"]:
        # Preserve missing/unknown in the denominators instead of listwise deleting.
        values = df[stratifier].astype("string").fillna("Missing/unknown")
        for name, sub in df.groupby(values, dropna=False, sort=True):
            row = {"stratifier": stratifier, "group": str(name), "n": int(len(sub))}
            for y in OUTCOMES:
                if sub[y].isna().any() or not sub[y].isin([0, 1]).all():
                    raise ValueError(f"{y} must be complete and binary")
                row[f"{y}_n"] = int(sub[y].sum())
                row[f"{y}_pct"] = round(100 * float(sub[y].mean()), 2)
            for choice in ["neither", "CTA only", "MRA only", "both"]:
                row[f"vascular_{choice.replace(' ', '_')}_n"] = int(sub["vascular_pattern"].astype(str).eq(choice).sum())
            frames.append(row)
    return pd.DataFrame(frames)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "results/phase1/cohort_age50.parquet")
    parser.add_argument("--output", type=Path, default=ROOT / "results/phase1/descriptive_age50.csv")
    args = parser.parse_args()
    table = describe(pd.read_parquet(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    print(f"Saved {len(table)} aggregate rows to {args.output}")


if __name__ == "__main__":
    main()
