"""Step 6: preliminary age/year-adjusted models of binary imaging receipt.

THIS IS A METHODS CHECK, NOT A PUBLICATION-READY CLINICAL MODEL.
No vascular risks, NIHSS, institutional factors, MRI contraindications or
insurance information are available in the current derived cohort.

Fit a binomial GLM and marginally standardize to each analysis subset,
reporting percentage-point risk differences with robust delta-method CIs.
Compare all patients against known-race and missing-race subsets to
illustrate selection sensitivity. Neither subgroup eliminates confounding.
No row-level data are written to output.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.special import expit
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
OUTCOMES = ("MRI_received", "vascular_received")
FORMULA_ADJUSTMENTS = "age_at_stroke + C(dx_year)"
SEX_EFFECT = "Men minus Women"


def fit_marginal_difference(df: pd.DataFrame, outcome: str) -> dict:
    """Estimate standardized receipt probabilities (men vs women).

    Adjust only for age and diagnosis year. Uses a robust sandwich
    covariance and the delta method for the marginal mean difference.
    All patient rows stay in memory and are never returned or written.
    """
    if outcome not in OUTCOMES:
        raise ValueError(f"Unsupported binary imaging outcome: {outcome}")
    needed = ["sex", "age_at_stroke", "dx_year", outcome]
    if any(x not in df.columns for x in needed):
        raise ValueError(f"Missing fields: {sorted(set(needed) - set(df.columns))}")
    d = df[needed].copy()
    if d.isna().any().any():
        raise ValueError("Incomplete outcome/sex/age/year data; review missing-data rules.")
    if not d[outcome].isin([0, 1]).all():
        raise ValueError("Outcome must be binary, with 0/1 values.")
    if set(d["sex"].unique()) != {"Men", "Women"}:
        raise ValueError("Both Men and Women groups must be present.")
    age = pd.to_numeric(d["age_at_stroke"], errors="coerce")
    if age.isna().any() or not np.isfinite(age).all() or age.le(18).any():
        raise ValueError("Invalid age data.")
    d["age_at_stroke"] = age
    if d[outcome].nunique() < 2:
        raise ValueError("At least two outcome classes are required.")

    formula = (f"{outcome} ~ C(sex, Treatment(reference='Women'))"
               f" + {FORMULA_ADJUSTMENTS}")
    fit = smf.glm(formula, data=d, family=sm.families.Binomial()).fit(cov_type="HC3")
    info = fit.model.data.design_info
    male = d.copy()
    female = d.copy()
    male["sex"] = "Men"
    female["sex"] = "Women"
    male_x = np.asarray(patsy.build_design_matrices([info], male)[0])
    female_x = np.asarray(patsy.build_design_matrices([info], female)[0])
    beta = fit.params.to_numpy()
    pm = expit(male_x @ beta)
    pf = expit(female_x @ beta)

    # Gradient of averaged logistic risks, evaluated over identical
    # age/year distributions under each fixed sex category.
    grad = np.mean(
        pm[:, None] * (1 - pm[:, None]) * male_x
        - pf[:, None] * (1 - pf[:, None]) * female_x,
        axis=0,
    )
    var = float(grad @ fit.cov_params().to_numpy() @ grad)
    se = float(np.sqrt(max(var, 0.0)))
    diff = float(np.mean(pm) - np.mean(pf))
    z = norm.ppf(.975)
    return {
        "outcome": outcome,
        "n": int(len(d)),
        "men_n": int((d["sex"] == "Men").sum()),
        "women_n": int((d["sex"] == "Women").sum()),
        "adjusted_men_pct": float(100 * np.mean(pm)),
        "adjusted_women_pct": float(100 * np.mean(pf)),
        "men_minus_women_pp": float(100 * diff),
        "ci_low_pp": float(100 * (diff - z * se)),
        "ci_high_pp": float(100 * (diff + z * se)),
        "p_value": float(2 * norm.sf(abs(diff / se))) if se > 0 else np.nan,
        "adjustment": "Age at stroke and diagnosis year ONLY",
    }


def analyze(df: pd.DataFrame) -> pd.DataFrame:
    if "race" not in df.columns:
        raise ValueError("Missing race variable for selection sensitivity.")
    race = df["race"].astype("string").str.strip().str.lower()
    known = race.notna() & ~race.isin(["unknown", "xxx", ""])
    frames = []
    for label, part in (
        ("all", df),
        ("race_known", df.loc[known]),
        ("race_missing_or_unknown", df.loc[~known]),
    ):
        for outcome in OUTCOMES:
            result = fit_marginal_difference(part, outcome)
            result["subset"] = label
            frames.append(result)
    return pd.DataFrame(frames)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "results/phase1/cohort_age50.parquet")
    parser.add_argument("--output", type=Path, default=ROOT / "results/phase1/minimal_models_age50.csv")
    args = parser.parse_args()
    models = analyze(pd.read_parquet(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    models.to_csv(args.output, index=False)
    print(f"Preliminary model summaries saved locally: {args.output}")
    print("These models adjust ONLY for age and diagnosis year.")
    print("STOP: these estimates cannot support clinical-disparity conclusions.")


if __name__ == "__main__":
    main()
