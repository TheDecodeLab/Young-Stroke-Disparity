"""Step 13: privacy-conscious audit of original, unfiltered TriNetX exports.

Use ORIGINAL diagnosis, procedure and demographic exports, NOT the derived
imaging-linked file. This diagnostic does not construct a research cohort.
It writes aggregate counts and column names only. Report neither patient IDs
nor row examples. Passing this audit does not prove encounter linkage.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "diagnoses": {"patient_id", "code", "date", "principal_diagnosis_indicator"},
    "procedures": {"patient_id", "code", "date"},
    "demographics": {"patient_id", "sex", "year_of_birth"},
}
ENCOUNTER_FIELDS = {"encounter_id", "visit_id", "admission_id", "encounter_num",
                    "visit_occurrence_id", "encounterid", "encounter_number"}
# CPT sets are diagnostic candidate groups, not a finalized codebook.
CODES = {
    "ct_brain": {"70450", "70460", "70470"},
    "cta_head": {"70496"},
    "cta_neck": {"70498"},
    "mri_brain": {"70551", "70552", "70553"},
    "mra_head": {"70544", "70545", "70546"},
    "mra_neck": {"70547", "70548", "70549"},
}


def _dates(value: pd.Series) -> pd.Series:
    """Parse YYYYMMDD and ISO dates without exporting date values."""
    s = value.astype("string").str.strip()
    compact = s.str.fullmatch(r"\d{8}").fillna(False)
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    if compact.any():
        out.loc[compact] = pd.to_datetime(s.loc[compact], format="%Y%m%d", errors="coerce")
    if (~compact).any():
        out.loc[~compact] = pd.to_datetime(s.loc[~compact], errors="coerce", format="mixed")
    return out


def inspect_frames(kind: str, batches: Iterable[pd.DataFrame], columns: list[str]) -> dict:
    """Accumulate aggregate diagnostics; no identifiers or row excerpts returned."""
    if kind not in REQUIRED:
        raise ValueError(f"Unrecognized source: {kind}")
    cols = set(columns)
    missing = sorted(REQUIRED[kind] - cols)
    encounters = sorted(x for x in columns if x.lower() in ENCOUNTER_FIELDS)
    report = {
        "kind": kind, "columns": sorted(map(str, columns)),
        "missing_required_columns": missing,
        "encounter_key_candidates": encounters,
        "patient_id_count_available": "patient_id" in cols,
        "rows_scanned": 0,
    }
    patient_ids = set()
    total_missing_patient_id = 0
    date_invalid = 0
    date_years = Counter()
    principal_years = Counter()
    code_hits = Counter()
    candidates_patient_ids = set()
    sex_missing = 0
    birthyear_missing = 0
    ambiguous_principal = 0
    encounters_missing = Counter()
    for df in batches:
        report["rows_scanned"] += len(df)
        if "patient_id" in df:
            valid = df["patient_id"].notna()
            total_missing_patient_id += int((~valid).sum())
            patient_ids.update(df.loc[valid, "patient_id"].tolist())
        for key in encounters:
            encounters_missing[key] += int(df[key].isna().sum())
        if kind == "demographics":
            if "sex" in df:
                text = df["sex"].astype("string").str.lower().str.strip()
                sex_missing += int((text.isna() | text.isin(["", "unknown", "xxx"])).sum())
            if "year_of_birth" in df:
                yob = pd.to_numeric(df["year_of_birth"], errors="coerce")
                birthyear_missing += int(yob.isna().sum())
            continue
        if "date" in df:
            parsed = _dates(df["date"])
            date_invalid += int(parsed.isna().sum())
            year = parsed.dt.year
            for key, num in year.value_counts().items():
                date_years[int(key)] += int(num)
        else:
            year = pd.Series(pd.NA, index=df.index)
        if "code" not in df:
            continue
        code = df["code"].astype("string").str.strip().str.upper()
        if kind == "diagnoses":
            if "principal_diagnosis_indicator" not in df:
                continue
            principal_value = df["principal_diagnosis_indicator"].astype("string").str.strip().str.upper()
            principal = principal_value.eq("P").fillna(False)
            # I63 is a potential ICD-10-CM AIS family, not a validated cohort definition.
            icd10_ischemic = code.str.fullmatch(r"I63(?:\..+)?").fillna(False)
            retinal = code.str.fullmatch(r"H34\.1(?:\d*)?").fillna(False)
            cohort_window = year.isin([2018, 2019])
            matched = principal & icd10_ischemic & cohort_window
            retinal_match = principal & retinal & cohort_window
            code_hits["principal_I63_2018_2019_rows"] += int(matched.sum())
            code_hits["principal_H34_1_2018_2019_rows"] += int(retinal_match.sum())
            ambiguous_principal += int((principal_value.isna() | principal_value.eq("")).sum())
            if "patient_id" in df:
                candidates_patient_ids.update(df.loc[matched & df["patient_id"].notna(), "patient_id"].tolist())
            for y in (2018, 2019):
                principal_years[y] += int((matched & year.eq(y)).sum())
        elif kind == "procedures":
            for label, codes in CODES.items():
                flag = code.isin(codes) & year.isin([2018, 2019])
                code_hits[f"{label}_2018_2019_rows"] += int(flag.sum())
    report.update({
        "distinct_patient_ids": len(patient_ids) if "patient_id" in cols else None,
        "rows_missing_patient_id": total_missing_patient_id if "patient_id" in cols else None,
        "rows_missing_encounter_keys": dict(encounters_missing),
    })
    if kind == "demographics":
        report["sex_missing_or_unknown_n"] = sex_missing
        report["birthyear_missing_n"] = birthyear_missing
    else:
        report["invalid_or_missing_date_n"] = date_invalid if "date" in cols else None
        report["date_rows_by_year"] = {str(y): date_years.get(y, 0) for y in (2018, 2019)}
        report["code_group_row_counts"] = dict(sorted(code_hits.items()))
        if kind == "diagnoses":
            report["principal_I63_2018_2019_unique_patients"] = len(candidates_patient_ids)
            report["principal_I63_rows_by_year"] = {str(y): principal_years.get(y, 0) for y in (2018, 2019)}
            report["missing_principal_indicator_n"] = ambiguous_principal
    report["ready_for_reconstruction"] = False
    report["needs_review"] = [
        "Confirm these are ORIGINAL unfiltered source tables and the applicable research/data-use approvals.",
        "Confirm ischemic-stroke diagnosis codes, admission/index rules and CPT codebook with clinical investigators.",
        "Identify stable encounter/admission identifiers across both event tables, or document date-linkage ambiguity.",
        "Verify patient-level demographics, age, missingness and index timing before any cohort assembly.",
    ]
    return report


def inspect_source(path: Path, kind: str, max_rows: int = 5_000_000) -> dict:
    """Read local parquet/CSV in batches, or inspect schema only if too large."""
    if not path.exists():
        return {"kind": kind, "file": path.name, "status": "not_found"}
    suffix = path.suffix.lower()
    if path.is_dir():
        import pyarrow.dataset as ds
        dataset = ds.dataset(str(path), format="parquet")
        names = dataset.schema.names
        rows = dataset.count_rows()
        if rows > max_rows:
            return {"kind": kind, "file": path.name, "status": "metadata_only_large",
                    "columns": names, "rows": rows,
                    "encounter_key_candidates": [x for x in names if x.lower() in ENCOUNTER_FIELDS]}
        needed = sorted(set(names) & (REQUIRED[kind] | ENCOUNTER_FIELDS))
        stream = (batch.to_pandas() for batch in dataset.scanner(
            columns=needed, batch_size=50_000).to_batches())
    elif suffix == ".parquet":
        import pyarrow.parquet as pq
        parquet = pq.ParquetFile(path)
        names = parquet.schema_arrow.names
        if parquet.metadata.num_rows > max_rows:
            return {"kind": kind, "file": path.name, "status": "metadata_only_large",
                    "columns": names, "rows": parquet.metadata.num_rows,
                    "encounter_key_candidates": [x for x in names if x.lower() in ENCOUNTER_FIELDS]}
        needed = sorted(set(names) & (REQUIRED[kind] | ENCOUNTER_FIELDS))
        stream = (x.to_pandas() for x in parquet.iter_batches(batch_size=50_000, columns=needed))
    elif suffix == ".csv":
        names = pd.read_csv(path, nrows=0).columns.tolist()
        needed = sorted(set(names) & (REQUIRED[kind] | ENCOUNTER_FIELDS))
        stream = pd.read_csv(path, chunksize=50_000, usecols=needed, dtype="string")
    else:
        raise ValueError(f"Only .parquet and .csv source files are supported: {path.name}")
    result = inspect_frames(kind, stream, names)
    result["file"] = path.name
    result["status"] = "inspected"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for kind in REQUIRED:
        parser.add_argument(f"--{kind}", type=Path, help=f"Local original {kind} Parquet/CSV export")
    parser.add_argument("--max-rows", type=int, default=5_000_000)
    parser.add_argument("--output", type=Path, default=ROOT / "results/phase1/source_readiness.json")
    args = parser.parse_args()
    if not any(getattr(args, name) for name in REQUIRED):
        parser.error("Provide at least one of --diagnoses, --procedures or --demographics")
    if args.max_rows < 1:
        parser.error("--max-rows must be positive")
    reports = [inspect_source(path, kind, args.max_rows)
               for kind in REQUIRED if (path := getattr(args, kind)) is not None]
    final = {"stage": "ORIGINAL_SOURCE_READINESS_AUDIT_ONLY",
             "sources": reports,
             "conclusion": "No population imaging inference until eligibility and event linkage are validated."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Saved aggregate and schema-only report to", args.output)
    for result in reports:
        print(result["kind"], result["status"], "rows", result.get("rows_scanned", result.get("rows")),
              "missing columns", result.get("missing_required_columns", "not checked"))
    print("STOP: source inventory alone does not validate cohort eligibility.")


if __name__ == "__main__":
    main()
