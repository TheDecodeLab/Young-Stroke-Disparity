"""Step 9: aggregate-only audit of original, pre-exclusion Parquet candidates.

The candidate files may contain CT-only stroke patients omitted by the
original notebook. This script does NOT reconstruct the clinical cohort.
It never writes patient identifiers or record-level data. A patient-level
CT-only flag is distinct from CT-only at a specific diagnosis date.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODALITIES = ("CT", "MRI", "CTA", "MRA")
ADVANCED = ("MRI", "CTA", "MRA")
MISSING = {"", "unknown", "xxx", "none", "nan", "null"}


def audit_batches(batches: Iterable[pd.DataFrame], columns: list[str]) -> dict:
    """Inspect batches in memory; return aggregate diagnostics only.

    Procedure-level input uses `category` and `patient_id`. CT-only
    patient counts are pooled across dates; date-specific counts, when
    available, remain unverified proxies for index encounters.
    """
    cols = set(columns)
    kind = ("procedure_events" if {"patient_id", "category"} <= cols
            else "derived_counts" if set(ADVANCED) <= cols
            else "schema_only")
    report: dict = {"table_type": kind, "rows_scanned": 0, "warnings": []}
    if kind == "schema_only":
        report["warnings"].append("Unrecognized layout: review source schema.")
        for frame in batches:
            report["rows_scanned"] += len(frame)
        return report

    if kind == "procedure_events":
        patients = {name: set() for name in MODALITIES}
        row_counts = Counter()
        date_col = next((x for x in ("datetime_dx", "date_dx") if x in cols), None)
        patient_dates: dict[tuple[object, str], int] = defaultdict(int)
        missing_id = 0
        for frame in batches:
            report["rows_scanned"] += len(frame)
            missing_id += int(frame["patient_id"].isna().sum())
            subset_cols = ["patient_id", "category"] + ([date_col] if date_col else [])
            selected = frame[subset_cols].dropna(subset=["patient_id"])
            category = selected["category"].astype("string").str.strip().str.upper()
            for name in MODALITIES:
                part = selected.loc[category.eq(name)]
                row_counts[name] += len(part)
                patients[name].update(part["patient_id"].tolist())
                if date_col:
                    for pid, date in part[["patient_id", date_col]].itertuples(index=False, name=None):
                        if pd.notna(date):
                            patient_dates[(pid, str(date))] |= 1 << MODALITIES.index(name)
        ct = patients["CT"]
        other = set().union(*(patients[name] for name in ADVANCED))
        report.update({
            "unique_patients_any_modality": len(ct | other),
            "ct_patients_n": len(ct),
            "ct_only_patients_n": len(ct - other),
            "ct_plus_advanced_patients_n": len(ct & other),
            "procedure_rows_by_category": dict(row_counts),
            "unique_patients_by_category": {name: len(patients[name]) for name in MODALITIES},
            "rows_missing_patient_id": missing_id,
            "diagnosis_date_column": date_col,
        })
        if date_col:
            flags = [x for x in patient_dates.values() if x & 1]
            report.update({
                "distinct_patient_diagnosis_dates_n": len(patient_dates),
                "ct_linked_patient_diagnosis_dates_n": len(flags),
                "ct_only_patient_diagnosis_dates_n": sum(x == 1 for x in flags),
            })
            report["warnings"].append(
                "Patient+diagnosis-date is NOT an encounter ID; verify joins and index admissions."
            )
        report["warnings"].append(
            "Patient-level CT-only counts pool across events and do not validate the cohort."
        )
        return report

    seen_ids: set = set()
    duplicate_ids_n = 0
    positive = Counter()
    invalid = Counter()
    missing_demographic = Counter()
    demographic_total = Counter()
    all_advanced_zero_n = 0
    ct_only_n = 0
    age_min, age_max = None, None
    has_ct = "CT" in cols
    for frame in batches:
        report["rows_scanned"] += len(frame)
        if "patient_id" in cols:
            ids = frame["patient_id"].dropna()
            duplicate_ids_n += int(ids.duplicated().sum()) + int(ids.isin(seen_ids).sum())
            seen_ids.update(ids.tolist())
        values = {}
        for name in (*ADVANCED, *(("CT",) if has_ct else ())):
            raw = pd.to_numeric(frame[name], errors="coerce")
            values[name] = raw
            positive[name] += int(raw.gt(0).sum())
            invalid[name] += int((raw.isna() | raw.lt(0) | raw.mod(1).ne(0)).sum())
        no_advanced = pd.concat([values[m].eq(0) for m in ADVANCED], axis=1).all(axis=1)
        all_advanced_zero_n += int(no_advanced.sum())
        if has_ct:
            ct_only_n += int((values["CT"].gt(0) & no_advanced).sum())
        for name in ("race", "ethnicity"):
            if name in cols:
                x = frame[name].astype("string").str.strip().str.lower()
                missing_demographic[name] += int((x.isna() | x.isin(MISSING)).sum())
                demographic_total[name] += len(frame)
        age_col = next((x for x in ("age@stroke", "age_at_stroke") if x in cols), None)
        if age_col:
            age = pd.to_numeric(frame[age_col], errors="coerce").dropna()
            if len(age):
                age_min = min(age_min, float(age.min())) if age_min is not None else float(age.min())
                age_max = max(age_max, float(age.max())) if age_max is not None else float(age.max())
    report.update({
        "imaging_columns": [name for name in MODALITIES if name in cols],
        "rows_with_no_mri_cta_mra": all_advanced_zero_n,
        "ct_only_rows": ct_only_n if has_ct else None,
        "positive_rows_by_modality": dict(positive),
        "invalid_counts_by_modality": dict(invalid),
        "race_ethnicity_missing_or_unknown": {
            k: {"n": int(v), "denominator": int(demographic_total[k])}
            for k, v in missing_demographic.items()
        },
        "min_age": age_min, "max_age": age_max,
    })
    if "patient_id" in cols:
        report["distinct_patient_ids"] = len(seen_ids)
        report["duplicate_patient_id_rows"] = duplicate_ids_n
    if not has_ct:
        report["warnings"].append(
            "No explicit CT count: zero advanced imaging does not prove CT-only status."
        )
    if duplicate_ids_n:
        report["warnings"].append("Repeated patient IDs: verify index event and encounter rules.")
    report["warnings"].append(
        "Derived imaging counts cannot verify stroke diagnosis, CT eligibility, or temporal linkage."
    )
    return report


def audit_file(path: Path, max_rows: int, batch_size: int) -> dict:
    """Scan only audit-relevant Parquet columns in bounded batches."""
    if not path.is_file():
        return {"file": path.name, "status": "not_found"}
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(path)
    names = pf.schema_arrow.names
    report: dict = {
        "file": path.name,
        "status": "inspected",
        "parquet_rows": pf.metadata.num_rows,
        "parquet_row_groups": pf.metadata.num_row_groups,
        "columns": names,
    }
    if pf.metadata.num_rows > max_rows:
        report["status"] = "metadata_only_large_file"
        report["warning"] = "Scan skipped at --max-rows limit; increase if local memory permits."
        return report
    needed = [name for name in (
        "patient_id", "category", "datetime_dx", "date_dx",
        "MRI", "CTA", "MRA", "CT", "race", "ethnicity",
        "age@stroke", "age_at_stroke",
    ) if name in names]
    batches = (batch.to_pandas() for batch in pf.iter_batches(
        batch_size=batch_size, columns=needed))
    report.update(audit_batches(batches, names))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/phase1/recovery_candidate_audit.json")
    parser.add_argument("--max-rows", type=int, default=5_000_000)
    parser.add_argument("--batch-size", type=int, default=50_000)
    args = parser.parse_args()
    if args.max_rows < 1 or args.batch_size < 1:
        parser.error("Row limit and batch size must be positive")
    reports = [audit_file(path, args.max_rows, args.batch_size) for path in args.files]
    result = {
        "purpose": "LOCAL aggregate-only recovery candidate audit",
        "files": reports,
        "decision": "Reconstruct stroke index cohort and preserve CT-only cases before inference.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Saved aggregate report:", args.output)
    for r in reports:
        print(r["file"], r["status"], "rows:", r.get("parquet_rows"),
              "CT-only patients:", r.get("ct_only_patients_n"),
              "CT-only rows:", r.get("ct_only_rows"))
    print("Do not publish patient-level inputs or derived cohorts.")


if __name__ == "__main__":
    main()
