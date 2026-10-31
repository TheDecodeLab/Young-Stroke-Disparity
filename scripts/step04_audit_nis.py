"""Step 4: audit repository NIS summary CSVs against manuscript v7.

These CSVs contain age-stratum summaries, NOT NIS microdata or design
variables. We cannot confirm survey methods or infer age-bin boundaries.
Never silently assign a stratum to a specific age interval.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def extract_ischaemic_rows(sex_csv: Path, race_csv: Path) -> pd.DataFrame:
    items = []
    for path, variable in [(sex_csv, "sex"), (race_csv, "race")]:
        df = pd.read_csv(path, encoding="utf-8-sig")
        group = "FEMALE" if variable == "sex" else "RACE"
        needed = {"Age_Stratified", "DiseaseType", group, "weighted_n_patients", "Mean_MRI", "MRI_p-value"}
        if missing := needed - set(df.columns):
            raise ValueError(f"{path.name} missing: {sorted(missing)}")
        df = df[df["DiseaseType"].astype("string").str.strip().eq("Ischemic")].copy()
        for _, x in df.iterrows():
            items.append({
                "source": path.name, "comparison": variable,
                "age_stratum_code": str(x["Age_Stratified"]),
                "group": str(x[group]), "weighted_n": float(x["weighted_n_patients"]),
                "mean_mri": float(x["Mean_MRI"]), "reported_p": float(x["MRI_p-value"]),
            })
    return pd.DataFrame(items)


def assess_manuscript_match(rows: pd.DataFrame, tolerance: float = .005) -> dict:
    """Check where manuscript's 0.80 White and 0.74 Black values occur.

    The manuscript also says p<0.05. This check is diagnostic, not proof of error:
    the v7 analysis may use another input revision or aggregation.
    """
    race = rows[rows["comparison"].eq("race")]
    matches = []
    for stratum, subset in race.groupby("age_stratum_code"):
        white = subset[subset["group"].eq("White")]
        black = subset[subset["group"].eq("Black")]
        if len(white) != 1 or len(black) != 1:
            continue
        w, b = white.iloc[0], black.iloc[0]
        if abs(w.mean_mri - .80) <= tolerance and abs(b.mean_mri - .74) <= tolerance:
            matches.append({
                "stratum": str(stratum), "white_mean_mri": float(w.mean_mri),
                "black_mean_mri": float(b.mean_mri), "csv_p": float(w.reported_p),
                "consistent_with_manuscript_p_lt_0_05": bool(w.reported_p < .05),
            })
    return {
        "manuscript_v7_reported": {"white_mri": .80, "black_mri": .74, "p_less_than": .05},
        "matching_strata_in_current_csvs": matches,
        "caveat": "Age-bin definitions and original NIS code unavailable; no validation claim is justified.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sex-csv", type=Path, default=ROOT / "dataset/MRI_CT_Summary_with_pvalues.csv")
    parser.add_argument("--race-csv", type=Path, default=ROOT / "dataset/MRI_CT_Race_Summary_with_pvalues.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "results/phase1/nis_stratum_audit.csv")
    args = parser.parse_args()
    rows = extract_ischaemic_rows(args.sex_csv, args.race_csv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(args.output, index=False)
    comparison = assess_manuscript_match(rows)
    import json
    path = args.output.with_suffix(".json")
    path.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    print(f"Saved stratum summaries: {args.output}")
    print(f"Manuscript comparison: {path}")
    for item in comparison["matching_strata_in_current_csvs"]:
        print(f"Potential matching race stratum {item['stratum']}: CSV p={item['csv_p']:.4f}; "
              f"matches manuscript p<0.05? {item['consistent_with_manuscript_p_lt_0_05']}")
    print("STOP: verify the source NIS scripts, strata definitions, and survey design before interpreting.")


if __name__ == "__main__":
    main()
