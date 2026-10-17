"""Step 19-21: secure, checkpointed diagnosis-first reconstruction workflow.

This is a PROVISIONAL patient/date-linked cohort, not an encounter-
validated hospitalization cohort. Do not use for manuscript inference
until codebooks, eligibility, linkage and governance are reviewed.

SMOKE scans the first 100,000 diagnosis rows only and never permits
downstream work from the incomplete database.
FULL chains: original diagnosis -> demographics -> procedure receipt ->
aggregate integrity checks, directly from one local authorized ZIP.

Patient-level records exist ONLY in owner-only SQLite databases in a
chosen private workdir OUTSIDE the repository. Output JSON is aggregate
only. A complete stage is skipped on rerun; partial stages abort instead
of silently creating a mixture of incomplete records.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import sqlite3
import stat
from zipfile import ZipFile

import pandas as pd

try:
    from scripts.step18_diagnosis_index import scan as scan_diagnoses, ensure_private_dir
except ModuleNotFoundError:  # python scripts/step19_21_reconstruct.py
    from step18_diagnosis_index import scan as scan_diagnoses, ensure_private_dir


ROOT = Path(__file__).resolve().parents[1]
# Historical manuscript CPT definitions, not an endorsed complete codebook.
CPT = {
    "70450": "CT", "70460": "CT", "70470": "CT",
    "70496": "CTA",
    "70544": "MRA", "70545": "MRA",
    "70551": "MRI", "70552": "MRI", "70553": "MRI",
}
STAGES = {
    "diagnosis": "step18_diagnosis_index.sqlite",
    "cohort": "step19_age_cohort.sqlite",
    "imaging": "step20_imaging_events.sqlite",
}
WINDOW_START = "20171225"
WINDOW_END = "20200107"


def manifest_rows(zf: ZipFile, member: str) -> int:
    """Fail closed if ZIP manifest cannot certify a complete source scan."""
    if "manifest.csv" not in zf.namelist() or zf.getinfo("manifest.csv").file_size > 1048576:
        raise ValueError("Missing or oversized ZIP manifest")
    with zf.open("manifest.csv") as handle:
        rows = csv.DictReader((line.decode("utf-8-sig") for line in handle))
        for row in rows:
            if row.get("file", "").strip() == member:
                count = str(row.get("row_count", "")).strip().replace(",", "")
                if count.isdigit():
                    return int(count)
    raise ValueError(f"Manifest lacks declared row count for {member}")


def source_signature(zf: ZipFile) -> dict:
    """A fast archive fingerprint to prohibit mixing different exports."""
    import hashlib
    members = ["manifest.csv", "diagnosis.csv", "patient.csv", "procedure.csv"]
    values = []
    for member in members:
        z = zf.getinfo(member)
        values.append(f"{member}:{z.CRC}:{z.file_size}:{z.compress_size}")
    return {"archive_members_sha256": hashlib.sha256("|".join(values).encode()).hexdigest()}


def verify_signature(zip_path: Path, private: Path) -> None:
    with ZipFile(zip_path) as zf:
        current = source_signature(zf)
    path = private / "source_signature.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != current:
            raise ValueError("Archive metadata changed: refuse to mix different source versions")
    else:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(current, f, sort_keys=True)


def stage_paths(base: Path, kind: str) -> tuple[Path, Path]:
    name = STAGES[kind]
    return base / name, base / (name.replace(".sqlite", ".partial.sqlite"))


def db_complete(path: Path) -> bool:
    if not path.is_file():
        return False
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as con:
        return bool(con.execute(
            "SELECT value FROM scan_state WHERE key='scan_complete'"
        ).fetchone()[0] == "1")


def create_db(path: Path, schema: str) -> sqlite3.Connection:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite incomplete or previous work: {path.name}")
    con = sqlite3.connect(path)
    os.chmod(path, 0o600)
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("PRAGMA synchronous=FULL")
    con.executescript(schema)
    con.execute("CREATE TABLE scan_state(key TEXT PRIMARY KEY, value TEXT)")
    con.execute("INSERT INTO scan_state VALUES ('scan_complete','0')")
    con.commit()
    return con


def finalize_db(conn: sqlite3.Connection, partial: Path, target: Path) -> None:
    conn.execute("UPDATE scan_state SET value='1' WHERE key='scan_complete'")
    conn.commit()
    conn.close()
    partial.replace(target)


def normalize_sex(text: pd.Series) -> pd.Series:
    return text.str.strip().str.upper().map({
        "F": "Female", "FEMALE": "Female",
        "M": "Male", "MALE": "Male",
    })


def choose_eligible_demographics(frame: pd.DataFrame, index_dates: dict,
                                 min_age: int, max_age: int) -> tuple[list[tuple], dict]:
    """Filter only after index-date selection, independent of procedures."""
    required = {"patient_id", "sex", "race", "ethnicity", "year_of_birth"}
    if missing := required - set(frame):
        raise ValueError(f"Missing patient columns: {sorted(missing)}")
    subset = frame.loc[frame["patient_id"].isin(index_dates)].copy()
    if subset.empty:
        return [], {"source_rows": len(frame), "linked_rows": 0,
                    "eligible_rows": 0, "missing_yob_rows": 0,
                    "unrecognized_sex_rows": 0, "out_of_age_rows": 0}
    sex = normalize_sex(subset["sex"])
    dob = pd.to_numeric(subset["year_of_birth"], errors="coerce")
    dates = subset["patient_id"].map(index_dates)
    year = pd.to_numeric(dates.str[:4], errors="coerce")
    age = year - dob
    valid = (sex.notna() & dob.between(1850, 2020) &
             age.between(min_age, max_age) & year.isin([2018, 2019]))
    retained = subset.loc[valid]
    rows = [(str(pid), str(date), str(sx), int(a),
             str(race), str(ethn))
            for pid, date, sx, a, race, ethn in zip(
                retained["patient_id"], dates.loc[valid], sex.loc[valid],
                age.loc[valid], retained["race"], retained["ethnicity"])]
    audit = {
        "source_rows": len(frame),
        "linked_rows": len(subset),
        "eligible_rows": len(rows),
        "missing_yob_rows": int(dob.isna().sum()),
        "unrecognized_sex_rows": int(sex.isna().sum()),
        "out_of_age_rows": int((~age.between(min_age, max_age)).sum()),
    }
    return rows, audit


def build_demographic_cohort(zip_path: Path, index_file: Path, base: Path,
                             min_age: int, max_age: int, chunk_rows: int) -> dict:
    """Create age/sex-eligible cohort from a FULL diagnosis-first index."""
    if not db_complete(index_file):
        raise ValueError("Cannot use missing or INCOMPLETE diagnosis index")
    complete, partial = stage_paths(base, "cohort")
    if partial.exists():
        raise FileExistsError("Incomplete demographic stage exists; inspect it locally")
    if complete.exists():
        if not db_complete(complete):
            raise ValueError("Previously completed demographic DB has invalid state")
        with sqlite3.connect(f"file:{complete}?mode=ro", uri=True) as con:
            config = dict(con.execute("SELECT key,value FROM scan_state"))
            if (config.get("min_age"), config.get("max_age")) != (str(min_age), str(max_age)):
                raise ValueError("Cannot reuse demographic index with a different age interval")
            n = con.execute("SELECT COUNT(*) FROM eligible").fetchone()[0]
        return {"stage": "demographics", "reused_complete": True, "eligible_n": n,
                "min_age": min_age, "max_age": max_age}

    with sqlite3.connect(f"file:{index_file}?mode=ro", uri=True) as con:
        indexes = {pid: date for pid, date in con.execute(
            "SELECT patient_id,index_date FROM first_principal_I63"
        )}
    totals = Counter()
    conn = create_db(partial, """CREATE TABLE eligible(
        patient_id TEXT PRIMARY KEY, index_date TEXT NOT NULL,
        sex TEXT NOT NULL, age INTEGER NOT NULL,
        race TEXT, ethnicity TEXT);""")
    try:
        with ZipFile(zip_path) as zf:
            declared = manifest_rows(zf, "patient.csv")
            with zf.open("patient.csv") as src:
                reader = pd.read_csv(src, usecols=["patient_id", "sex", "race",
                                      "ethnicity", "year_of_birth"], dtype="string",
                                     chunksize=chunk_rows, keep_default_na=False)
                for frame in reader:
                    records, audit = choose_eligible_demographics(frame, indexes,
                                                                 min_age, max_age)
                    totals.update(audit)
                    if records:
                        # A duplicate eligible patient is an error, not an averaging rule.
                        conn.executemany(
                            "INSERT INTO eligible VALUES (?,?,?,?,?,?)", records)
                    conn.commit()
            if totals["source_rows"] != declared:
                raise ValueError("Incomplete demographic source scan relative to manifest")
        n = conn.execute("SELECT COUNT(*) FROM eligible").fetchone()[0]
        if n != totals["eligible_rows"]:
            raise ValueError("Duplicate or inconsistent demographic eligibility counts")
        conn.executemany("INSERT INTO scan_state VALUES (?,?)",
                         [("min_age", str(min_age)), ("max_age", str(max_age))])
        finalize_db(conn, partial, complete)
    except Exception:
        conn.close()
        raise
    return {
        "stage": "demographics", "reused_complete": False,
        "source_rows": int(totals["source_rows"]),
        "diagnosis_index_patients": len(indexes),
        "matched_demographic_rows": int(totals["linked_rows"]),
        "eligible_n": int(n),
        "min_age": min_age, "max_age": max_age,
        "missing_yob_rows_among_matches": int(totals["missing_yob_rows"]),
        "unrecognized_sex_rows_among_matches": int(totals["unrecognized_sex_rows"]),
        "not_a_verified_hospitalization_cohort": True,
    }


def select_imaging_events(frame: pd.DataFrame, index_dates: dict) -> tuple[list[tuple], dict]:
    """Return distinct patient/modality/day receipts linked by +/-7 days."""
    required = {"patient_id", "code_system", "code", "date"}
    if missing := required - set(frame):
        raise ValueError(f"Missing procedure columns: {sorted(missing)}")
    system = frame["code_system"].str.strip().str.upper().eq("CPT")
    code = frame["code"].str.strip()
    day = frame["date"].str.strip()
    eligible = (system & code.isin(CPT) & day.between(WINDOW_START, WINDOW_END)
                & day.str.fullmatch(r"\d{8}").fillna(False)
                & frame["patient_id"].isin(index_dates))
    filtered = frame.loc[eligible, ["patient_id", "code", "date"]].copy()
    if filtered.empty:
        return [], {"source_rows": len(frame), "candidate_events": 0,
                    "within_window_events": 0}
    filtered["modality"] = filtered["code"].str.strip().map(CPT)
    ref = pd.to_datetime(filtered["patient_id"].map(index_dates),
                         format="%Y%m%d", errors="coerce")
    when = pd.to_datetime(filtered["date"], format="%Y%m%d", errors="coerce")
    offset = (when - ref).dt.days
    keep = offset.between(-7, 7)
    records = [(str(pid), str(mod), str(date))
               for pid, mod, date in filtered.loc[keep,
                   ["patient_id", "modality", "date"]].itertuples(index=False, name=None)]
    return records, {"source_rows": len(frame), "candidate_events": len(filtered),
                     "within_window_events": len(records)}


def imaging_counts(conn: sqlite3.Connection, cohort_conn: sqlite3.Connection) -> dict:
    """Aggregate receipts using a temporary local cohort table."""
    conn.execute("ATTACH DATABASE ? AS eligible_db",
                 (str(Path(cohort_conn.execute("PRAGMA database_list").fetchone()[2])),))
    query = """WITH flags AS (
      SELECT e.patient_id,
        MAX(CASE WHEN m.modality='CT' THEN 1 ELSE 0 END) AS ct,
        MAX(CASE WHEN m.modality='MRI' THEN 1 ELSE 0 END) AS mri,
        MAX(CASE WHEN m.modality='CTA' THEN 1 ELSE 0 END) AS cta,
        MAX(CASE WHEN m.modality='MRA' THEN 1 ELSE 0 END) AS mra
      FROM eligible_db.eligible e LEFT JOIN imaging_event m
        ON e.patient_id=m.patient_id GROUP BY e.patient_id)
    SELECT COUNT(*), COALESCE(SUM(ct),0), COALESCE(SUM(mri),0),
       COALESCE(SUM(cta),0), COALESCE(SUM(mra),0),
       COALESCE(SUM(CASE WHEN ct=1 AND mri=0 AND cta=0 AND mra=0 THEN 1 ELSE 0 END),0),
       COALESCE(SUM(CASE WHEN ct=1 AND (mri=1 OR cta=1 OR mra=1) THEN 1 ELSE 0 END),0),
       COALESCE(SUM(CASE WHEN ct=0 AND (mri=1 OR cta=1 OR mra=1) THEN 1 ELSE 0 END),0),
       COALESCE(SUM(CASE WHEN ct=0 AND mri=0 AND cta=0 AND mra=0 THEN 1 ELSE 0 END),0)
    FROM flags"""
    values = conn.execute(query).fetchone()
    fields = ("age_eligible_first_diagnosis_n", "ct_n", "mri_n", "cta_n", "mra_n",
              "ct_only_n", "ct_and_additional_n", "advanced_no_ct_n",
              "none_of_four_imaging_n")
    out = dict(zip(fields, map(int, values)))
    assert out["age_eligible_first_diagnosis_n"] == sum(
        out[k] for k in ("ct_only_n", "ct_and_additional_n",
                         "advanced_no_ct_n", "none_of_four_imaging_n"))
    conn.execute("DETACH DATABASE eligible_db")
    return out


def build_imaging(zip_path: Path, cohort_file: Path, base: Path, chunk_rows: int) -> dict:
    """Scan entire original procedure table, retaining CT-only patients."""
    if not db_complete(cohort_file):
        raise ValueError("Cannot scan imaging before complete eligible demographics")
    complete, partial = stage_paths(base, "imaging")
    if partial.exists():
        raise FileExistsError("Incomplete imaging stage exists; inspect it before rerun")
    if complete.exists():
        if not db_complete(complete):
            raise ValueError("Previously completed imaging DB has invalid state")
        import hashlib
        protocol = hashlib.sha256(
            json.dumps({"cpt": CPT, "window": [-7, 7]}, sort_keys=True).encode()
        ).hexdigest()
        with sqlite3.connect(f"file:{complete}?mode=ro", uri=True) as con:
            config = dict(con.execute("SELECT key,value FROM scan_state"))
            if config.get("imaging_protocol") != protocol:
                raise ValueError("Cannot reuse imaging database after CPT/window rules changed")
        return {"stage": "imaging", "reused_complete": True}
    with sqlite3.connect(f"file:{cohort_file}?mode=ro", uri=True) as eligible:
        index_dates = {pid: date for pid, date in eligible.execute(
            "SELECT patient_id,index_date FROM eligible")}
    counters = Counter()
    conn = create_db(partial, """CREATE TABLE imaging_event(
        patient_id TEXT NOT NULL, modality TEXT NOT NULL, procedure_date TEXT NOT NULL,
        PRIMARY KEY(patient_id,modality,procedure_date));""")
    try:
        with ZipFile(zip_path) as zf:
            declared = manifest_rows(zf, "procedure.csv")
            with zf.open("procedure.csv") as src:
                reader = pd.read_csv(src, usecols=["patient_id", "code_system",
                                         "code", "date"], dtype="string",
                                     chunksize=chunk_rows, keep_default_na=False)
                for frame in reader:
                    rows, audit = select_imaging_events(frame, index_dates)
                    counters.update(audit)
                    if rows:
                        conn.executemany(
                            "INSERT OR IGNORE INTO imaging_event VALUES (?,?,?)", rows)
                    conn.commit()
            if counters["source_rows"] != declared:
                raise ValueError("Incomplete procedure scan relative to manifest")
        saved_events = conn.execute("SELECT COUNT(*) FROM imaging_event").fetchone()[0]
        with sqlite3.connect(f"file:{cohort_file}?mode=ro", uri=True) as eligible:
            overview = imaging_counts(conn, eligible)
        import hashlib
        protocol = hashlib.sha256(
            json.dumps({"cpt": CPT, "window": [-7, 7]}, sort_keys=True).encode()
        ).hexdigest()
        conn.execute("INSERT INTO scan_state VALUES ('imaging_protocol',?)", (protocol,))
        finalize_db(conn, partial, complete)
    except Exception:
        conn.close()
        raise
    return {
        "stage": "imaging", "reused_complete": False,
        "source_rows": int(counters["source_rows"]),
        "candidate_CPT_events_in_selected_patients": int(counters["candidate_events"]),
        "all_matched_events_before_daily_dedup": int(counters["within_window_events"]),
        "distinct_modality_days_matched": int(saved_events),
        "historical_CPT_only": True,
        "temporal_link_only_not_verified_encounter": True,
        "aggregate_cohort_integrity": overview,
    }


def run_full(zip_path: Path, private_dir: Path, min_age: int = 19,
             max_age: int = 50, chunk_rows: int = 150000) -> dict:
    if not 0 < min_age <= max_age <= 120:
        raise ValueError("Invalid age interval")
    if chunk_rows < 100 or chunk_rows > 2_000_000:
        raise ValueError("Chunk size out of supported bounds")
    private = ensure_private_dir(private_dir)
    verify_signature(zip_path, private)
    stage18dir = ensure_private_dir(private / "diagnosis")
    diagnosis_file = stage18dir / STAGES["diagnosis"]
    partial18 = stage18dir / "step18_diagnosis_index.partial.sqlite"
    reports = []
    if partial18.exists():
        raise FileExistsError("Diagnosis stage is incomplete; inspect before rerunning")
    if diagnosis_file.exists():
        if not db_complete(diagnosis_file):
            raise ValueError("Existing diagnosis index was not marked complete")
        reports.append({"stage": "diagnosis", "reused_complete": True})
    else:
        reports.append(scan_diagnoses(zip_path, stage18dir,
                                     chunk_rows=chunk_rows, limit_rows=None))
    cohort_dir = ensure_private_dir(private / "demographics")
    reports.append(build_demographic_cohort(
        zip_path, diagnosis_file, cohort_dir, min_age, max_age, chunk_rows))
    imaging_dir = ensure_private_dir(private / "imaging")
    cohort_file = cohort_dir / STAGES["cohort"]
    reports.append(build_imaging(zip_path, cohort_file, imaging_dir, chunk_rows))
    return {
        "stage": "CHAINED_PROVISIONAL_RECONSTRUCTION",
        "source": "original_trinetx_zip",
        "stages": reports,
        "completed_all_source_scans": True,
        "validated_admission_cohort": False,
        "ready_for_manuscript_models": False,
        "caveats": [
            "Only 2018-2019 principal ICD-10-CM I63 diagnosis candidates were included.",
            "First qualifying diagnosis in that period does not prove incident first-ever stroke.",
            "No encounter ID; modality linkage is +/-7 day patient/date proxy.",
            "Only historical nine CPT codes are included; head/neck expansion awaits review.",
            "Race/ethnicity missingness and treatment indications remain unresolved.",
            "CT-only candidates are retained, but all rates must remain provisional.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--private-dir", type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    p.add_argument("--chunk-rows", type=int, default=150000)
    p.add_argument("--min-age", type=int, default=19)
    p.add_argument("--max-age", type=int, default=50)
    p.add_argument("--output", type=Path,
                   default=ROOT / "results/phase1/chained_reconstruction_audit.json")
    args = p.parse_args()
    if args.smoke:
        safe = ensure_private_dir(args.private_dir)
        scan_diagnoses(args.zip, safe / "smoke18",
                       chunk_rows=min(args.chunk_rows, 100000),
                       limit_rows=100000)
        report = {"stage": "SMOKE_ONLY", "sample_rows_limit": 100000,
                  "completed_all_source_scans": False,
                  "ready_for_manuscript_models": False}
    else:
        report = run_full(args.zip, args.private_dir, args.min_age,
                          args.max_age, args.chunk_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("Aggregate audit:", args.output)
    print("Full source scans completed:", report["completed_all_source_scans"])
    print("Encounter-level validation: NOT AVAILABLE. Manuscript inference: BLOCKED.")
    print("Patient-level data stayed inside private SQLite directory.")


if __name__ == "__main__":
    main()
