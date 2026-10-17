"""Step 8: detect imaging-dependent cohort selection from Step 7 summaries.

This audit uses aggregate counts only. It does not verify the source
eligibility criteria and cannot recover patients omitted upstream.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {"neither", "CTA only", "MRA only", "both"}


def audit_pattern_summary(df: pd.DataFrame) -> dict:
    needed = {"stratification", "group", "pattern", "group_n",
              "pattern_n", "MRI_within_pattern_n"}
    if missing := needed - set(df):
        raise ValueError(f"Missing columns: {sorted(missing)}")
    total = df[df["stratification"].eq("overall") & df["group"].eq("All")].copy()
    if len(total) != 4 or set(total["pattern"]) != PATTERNS:
        raise ValueError("Exactly four distinct overall patterns required")
    for col in ("group_n", "pattern_n", "MRI_within_pattern_n"):
        x = pd.to_numeric(total[col], errors="coerce")
        if x.isna().any() or (x < 0).any() or (x % 1 != 0).any():
            raise ValueError(f"Invalid count in {col}")
        total[col] = x.astype(int)
    if (total["MRI_within_pattern_n"] > total["pattern_n"]).any():
        raise ValueError("MRI count exceeds denominator")
    n = int(total["group_n"].iloc[0])
    if n < 1 or not total["group_n"].eq(n).all():
        raise ValueError("Inconsistent overall denominator")
    if int(total["pattern_n"].sum()) != n:
        raise ValueError("Four patterns do not partition the cohort")
    neither = total.set_index("pattern").loc["neither"]
    no_mri_cta_mra = int(neither["pattern_n"] - neither["MRI_within_pattern_n"])
    return {
        "cohort_n": n,
        "neither_cta_nor_mra_n": int(neither["pattern_n"]),
        "mri_in_neither_cta_nor_mra_n": int(neither["MRI_within_pattern_n"]),
        "no_mri_cta_mra_n": no_mri_cta_mra,
        "selection_bias_red_flag": bool(no_mri_cta_mra == 0),
        "ready_for_population_inference": False,
        "recommendation": "Rebuild the index cohort before imaging selection; retain CT-only records.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path,
                        default=ROOT / "results/phase1/modality_patterns_age50.csv")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/phase1/cohort_integrity_age50.json")
    args = parser.parse_args()
    report = audit_pattern_summary(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Patients: {report['cohort_n']:,}")
    print(f"With no MRI, CTA or MRA: {report['no_mri_cta_mra_n']:,}")
    print(f"Aggregate report: {args.output}")
    if report["selection_bias_red_flag"]:
        print("BLOCKED: CT-only patients were structurally excluded in historical notebook.")


if __name__ == "__main__":
    main()
