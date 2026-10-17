"""Steps 23-24: eligibility attrition and code-pattern audit.

Reuses COMPLETE private SQLite stage files and scans only original
patient.csv from the same authorized ZIP. No diagnosis/procedure rescans.
Writes only aggregate results, never individual clinical records.
Clinical inference remains BLOCKED without encounter linkage and code review.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import stat
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DX = "diagnosis/step18_diagnosis_index.sqlite"
DEM = "demographics/step19_age_cohort.sqlite"
IMG = "imaging/step20_imaging_events.sqlite"
CLASSES = ("CT only", "CT + additional", "Additional without CT", "None of four")


def load_complete(path: Path, table: str, columns: str) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError("Missing full private stage: " + path.name)
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as conn:
        if conn.execute("SELECT value FROM scan_state WHERE key='scan_complete'").fetchone() != ("1",):
            raise ValueError("Incomplete private stage: " + path.name)
        return pd.read_sql_query("SELECT " + columns + " FROM " + table, conn)


def masked(n: int) -> int | None:
    """Positive cells <11 cannot be exported. Further disclosure review required."""
    n = int(n)
    return None if 0 < n < 11 else n


def classify_imaging(eligible: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    if eligible["patient_id"].isna().any() or eligible["patient_id"].duplicated().any():
        raise ValueError("Invalid or duplicated eligible patients")
    if events.duplicated(["patient_id", "modality", "procedure_date"]).any():
        raise ValueError("Duplicate imaging modality-days")
    if not events["modality"].isin(("CT", "MRI", "CTA", "MRA")).all():
        raise ValueError("Unexpected imaging modality")
    if not set(events["patient_id"]).issubset(set(eligible["patient_id"])):
        raise ValueError("Imaging record for noneligible patient")
    out = eligible.copy()
    for modality in ("CT", "MRI", "CTA", "MRA"):
        ids = set(events.loc[events["modality"].eq(modality), "patient_id"])
        out[modality] = out["patient_id"].isin(ids)
    adv = out[["MRI", "CTA", "MRA"]].any(axis=1)
    out["imaging_class"] = "None of four"
    out.loc[out["CT"] & ~adv, "imaging_class"] = "CT only"
    out.loc[out["CT"] & adv, "imaging_class"] = "CT + additional"
    out.loc[~out["CT"] & adv, "imaging_class"] = "Additional without CT"
    return out


def analyze_codes(dx: pd.DataFrame, eligible: pd.DataFrame, events: pd.DataFrame) -> dict:
    if dx["patient_id"].isna().any() or dx["patient_id"].duplicated().any():
        raise ValueError("Invalid or duplicated diagnosis patients")
    flags = classify_imaging(eligible, events)
    x = flags.merge(dx[["patient_id", "index_date", "dx_code"]], on="patient_id",
                    how="left", validate="one_to_one",
                    suffixes=("_cohort", "_diagnosis"))
    if x["dx_code"].isna().any() or not x["index_date_cohort"].eq(x["index_date_diagnosis"]).all():
        raise ValueError("Diagnosis index and age cohort do not match")
    code = x["dx_code"].astype("string").str.strip().str.upper()
    if not code.str.fullmatch(r"I63(?:\.[0-9A-Z]+)?").fillna(False).all():
        raise ValueError("Unexpected code in diagnosis index")
    digit = code.str.extract(r"^I63\.(\d)", expand=False)
    x["family"] = ("I63." + digit).where(digit.notna(), "I63 stem")
    families = []
    for family, part in x.groupby("family", sort=True, observed=True):
        ct = part["imaging_class"].value_counts().to_dict()
        n = len(part)
        # Suppress the whole group when ANY class count is a small cell.
        small = 0 < n < 11 or any(0 < ct.get(cls, 0) < 11 for cls in CLASSES)
        if small:
            families.append({"icd10_family": str(family), "suppressed": True})
        else:
            families.append({"icd10_family": str(family), "suppressed": False,
                             "eligible_total": n,
                             "imaging_groups": {cls: int(ct.get(cls, 0)) for cls in CLASSES}})
    def unknown(series: pd.Series) -> pd.Series:
        s = series.astype("string").str.strip().str.lower()
        return s.isna() | s.isin(["", "unknown", "nan", "null", "xxx",
                                  "not recorded", "not reported"])
    missing = []
    for label, group in x.groupby("imaging_class", observed=True):
        missing.append({"imaging_class": str(label), "patients": int(len(group)),
                        "race_unknown_or_missing_n": masked(unknown(group["race"]).sum()),
                        "ethnicity_unknown_or_missing_n": masked(unknown(group["ethnicity"]).sum())})
    return {"first_decimal_digit_audit_by_imaging": families,
            "missing_race_ethnicity_by_imaging_group": missing,
            "disclosure_note": "Small families fully withheld; complementary disclosures must still be reviewed."}


def count_demographic_chunk(frame: pd.DataFrame, index: dict, saved_ids: set
                            ) -> tuple[Counter, set]:
    if not {"patient_id", "sex", "year_of_birth"}.issubset(frame.columns):
        raise ValueError("Required patient.csv columns missing")
    part = frame.loc[frame["patient_id"].isin(index),
                     ["patient_id", "sex", "year_of_birth"]].copy()
    counts = Counter()
    counts["index_rows_matched"] = len(part)
    if part.empty:
        return counts, set()
    if part["patient_id"].duplicated().any():
        raise ValueError("Source patient ID duplicated within chunk")
    yob = pd.to_numeric(part["year_of_birth"], errors="coerce")
    year = part["patient_id"].map(index).str.slice(0, 4).astype(int)
    age = year - yob
    recognized_sex = part["sex"].astype("string").str.strip().str.upper().isin(
        ["F", "M", "FEMALE", "MALE"])
    invalid_yob = yob.isna() | ~yob.between(1850, 2020)
    labels = pd.Series("age_over_50", index=part.index, dtype="string")
    labels.loc[age.lt(19)] = "age_under_19"
    labels.loc[age.between(19, 50)] = "eligible_19_50"
    labels.loc[~recognized_sex] = "unrecognized_sex"
    labels.loc[invalid_yob] = "missing_or_invalid_birth_year"
    for key, n in labels.value_counts().items():
        counts[str(key)] += int(n)
    qualified = set(part.loc[labels.eq("eligible_19_50"), "patient_id"])
    if not qualified.issubset(saved_ids):
        raise ValueError("Expected eligible patient not in completed cohort")
    counts["missing_birth_year_raw"] += int(yob.isna().sum())
    return counts, set(part["patient_id"])


def audit_demographic_source(zf: ZipFile, dx: pd.DataFrame, eligible: pd.DataFrame,
                             chunk_rows: int) -> dict:
    try:
        from scripts.step19_21_reconstruct import manifest_rows
    except ModuleNotFoundError:
        from step19_21_reconstruct import manifest_rows
    index = dict(dx[["patient_id", "index_date"]].itertuples(index=False, name=None))
    ids = set(eligible["patient_id"])
    seen = set()
    counts = Counter()
    expected = manifest_rows(zf, "patient.csv")
    with zf.open("patient.csv", "r") as stream:
        parts = pd.read_csv(stream, dtype="string", keep_default_na=False,
                            usecols=["patient_id", "sex", "year_of_birth"],
                            chunksize=chunk_rows, low_memory=False)
        for frame in parts:
            counts["source_rows"] += len(frame)
            part, found = count_demographic_chunk(frame, index, ids)
            if not seen.isdisjoint(found):
                raise ValueError("Duplicate source patient ID across chunks")
            seen.update(found)
            counts.update(part)
    if counts["source_rows"] != expected or len(seen) != len(index):
        raise ValueError("Source manifest or complete patient linkage failed")
    categories = ("missing_or_invalid_birth_year", "unrecognized_sex",
                  "age_under_19", "eligible_19_50", "age_over_50")
    if sum(counts[key] for key in categories) != len(index):
        raise ValueError("Exclusive demographic attrition categories do not sum to index")
    if counts["eligible_19_50"] != len(ids):
        raise ValueError("Completed age cohort fails source eligibility reconciliation")
    return {"original_patient_source_rows_verified": int(counts["source_rows"]),
            "index_patients": len(index),
            "source_patients_matched_to_index": len(seen),
            "exclusive_age_and_sex_attrition": {key: masked(counts[key]) for key in categories},
            "unparsed_or_missing_birth_year_n": masked(counts["missing_birth_year_raw"]),
            "saved_eligible_patients_reconciled_n": len(ids),
            "age_approximate": True,
            "exclusion_precedence": list(categories[:2]) + list(categories[2:])}


def run(private_dir: Path, zip_path: Path, chunk_rows: int = 150000,
        prior_step22: Path | None = None) -> dict:
    root = private_dir.expanduser().resolve()
    if not root.is_dir() or root == ROOT.resolve() or ROOT.resolve() in root.parents:
        raise ValueError("Private workdir must exist OUTSIDE Git")
    if stat.S_IMODE(root.stat().st_mode) & 0o077:
        raise ValueError("Private workdir must be owner-only")
    if chunk_rows < 100 or chunk_rows > 1000000:
        raise ValueError("Invalid chunk size")
    signature_file = root / "source_signature.json"
    if not signature_file.is_file():
        raise ValueError("Missing source signature")
    try:
        from scripts.step19_21_reconstruct import source_signature
    except ModuleNotFoundError:
        from step19_21_reconstruct import source_signature
    with ZipFile(zip_path) as zf:
        if source_signature(zf) != json.loads(signature_file.read_text(encoding="utf-8")):
            raise ValueError("ZIP differs from original completed reconstruction")
        dx = load_complete(root / DX, "first_principal_I63", "patient_id,index_date,dx_code")
        eligible = load_complete(root / DEM, "eligible",
                                 "patient_id,index_date,sex,age,race,ethnicity")
        events = load_complete(root / IMG, "imaging_event",
                               "patient_id,modality,procedure_date")
        code = analyze_codes(dx, eligible, events)
        demographic = audit_demographic_source(zf, dx, eligible, chunk_rows)
    if prior_step22 is not None:
        p = json.loads(prior_step22.read_text(encoding="utf-8"))
        if (p.get("stage") != "STEP22_LOCAL_SQLITE_VALIDATION_ONLY"
                or p.get("age_eligible_n") != len(eligible)
                or p.get("matched_distinct_modality_days") != len(events)
                or p.get("full_diagnosis_index_patients") != len(dx)):
            raise ValueError("Prior Step 22 reference does not reconcile")
    return {"stage": "STEPS23_24_ELIGIBILITY_AND_CODE_QC",
            "original_zip_member_scanned": "patient.csv",
            "diagnosis_procedure_source_records_rescanned": 0,
            "signature_reconciled": True,
            "step22_reference_compared": prior_step22 is not None,
            "demographic_attrition": demographic,
            "diagnosis_and_imaging_diagnostics": code,
            "clinical_inference_allowed": False,
            "limitations": [
                "Patient/date linked diagnosis is not a verified hospitalization",
                "Historical nine CPT code definitions omit relevant imaging codes",
                "Birth-year-only age and missing race/ethnicity limit representativeness",
                "ICD-10-CM first decimal digit is an audit category, not stroke phenotype",
                "Complementary suppression requires human disclosure review",
            ]}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--chunk-rows", type=int, default=150000)
    p.add_argument("--compare-step22", type=Path)
    p.add_argument("--output", type=Path,
                   default=ROOT / "results/phase1/step23_24_eligibility_qc.json")
    args = p.parse_args()
    result = run(args.private_dir, args.zip, args.chunk_rows, args.compare_step22)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("Aggregate-only eligibility and diagnosis code audit:", args.output)
    print("Original diagnosis/procedure rows rescanned: 0")
    print("Do not use for manuscript imaging or disparity inference.")


if __name__ == "__main__":
    main()
