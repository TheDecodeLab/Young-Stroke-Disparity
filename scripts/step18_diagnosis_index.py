"""Step 18: staged diagnosis-first index candidates from original ZIP.

Reads only original diagnosis.csv directly from the approved TriNetX ZIP.
Does NOT select patients based on any imaging procedure.
Selects principal (P) ICD-10-CM I63-family diagnoses in 2018-2019,
retaining each patient's earliest qualifying diagnosis in that period.

IMPORTANT: This is NOT a validated stroke admission, incident stroke,
or publication-ready cohort. There are no encounter keys in the source
ZIP. H34.1, ICD-9, nonprincipal and missing-principal diagnoses are NOT
silently included. Clinical codebook and lookback decisions are pending.

Sensitive patient identifiers/dates are stored only in a user-chosen,
access-restricted SQLite directory OUTSIDE this Git repository.
An interrupted scan leaves an explicitly incomplete .partial database.
No resumable ZIP seek is claimed. Summary JSON contains aggregates only.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ["patient_id", "code_system", "code", "principal_diagnosis_indicator", "date"]
YEARS = ("2018", "2019")
SOURCE = "diagnosis.csv"


def expected_rows(zf: ZipFile) -> int | None:
    """Read only the small manifest member for its declared row count."""
    if "manifest.csv" not in zf.namelist():
        return None
    info = zf.getinfo("manifest.csv")
    if info.file_size > 1048576:
        raise ValueError("Manifest too large for metadata-only read")
    with zf.open(info) as f:
        rows = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        for row in rows:
            if row.get("file", "").strip() == SOURCE:
                raw = (row.get("row_count") or "").replace(",", "").strip()
                return int(raw) if raw.isdigit() else None
    return None


def choose_principal_I63(chunk: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Return qualifying 2018-19 events and aggregate audit counts."""
    missing = set(COLUMNS) - set(chunk.columns)
    if missing:
        raise ValueError(f"Missing diagnosis columns: {sorted(missing)}")
    year = chunk["date"].str.slice(0, 4)
    in_year = year.isin(YEARS) & chunk["date"].str.fullmatch(r"\d{8}").fillna(False)
    code = chunk["code"].str.strip().str.upper()
    is_I63 = code.str.fullmatch(r"I63(?:\.[0-9A-Z]+)?").fillna(False)
    valid_system = chunk["code_system"].str.strip().str.upper().eq("ICD-10-CM")
    principal = chunk["principal_diagnosis_indicator"].str.strip().str.upper()
    selected = in_year & is_I63 & valid_system
    good = selected & principal.eq("P") & chunk["patient_id"].str.strip().ne("")
    candidate = chunk.loc[good, ["patient_id", "date", "code"]].copy()
    invalid_dates = 0
    if not candidate.empty:
        parsed = pd.to_datetime(candidate["date"], format="%Y%m%d", errors="coerce")
        invalid_dates = int(parsed.isna().sum())
        candidate = candidate.loc[parsed.notna()].copy()
    audit = {
        "rows_scanned": len(chunk),
        "in_year_icd10_I63_rows": int(selected.sum()),
        "in_year_icd10_I63_P_rows": int((selected & principal.eq("P")).sum()),
        "in_year_icd10_I63_unknown_principal_rows": int(
            (selected & ~principal.isin(["P", "S"])).sum()),
        "qualifying_missing_patient_id_rows": int(
            (selected & principal.eq("P") & chunk["patient_id"].str.strip().eq("")).sum()),
        "qualifying_invalid_calendar_date_rows": invalid_dates,
        "qualifying_rows_retained": len(candidate),
    }
    return candidate, audit


def ensure_private_dir(path: Path) -> Path:
    """Refuse repo-contained and group/world-readable clinical workdirs."""
    private = path.expanduser().resolve()
    repository = ROOT.resolve()
    if private == repository or repository in private.parents:
        raise ValueError("Patient-level SQLite workdir must be OUTSIDE the Git repository")
    if private.exists() and not private.is_dir():
        raise ValueError("Private directory path is not a directory")
    if not private.exists():
        private.mkdir(parents=True, mode=0o700)
    if stat.S_IMODE(private.stat().st_mode) & 0o077:
        raise ValueError("Private directory must not grant permissions to group/other")
    return private


def init_database(path: Path) -> sqlite3.Connection:
    if path.exists():
        raise FileExistsError(
            f"An incomplete/previous index exists at {path}. "
            "Inspect it first and choose a new private directory for a fresh scan."
        )
    conn = sqlite3.connect(path)
    os.chmod(path, 0o600)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute(
        "CREATE TABLE first_principal_I63 ("
        "patient_id TEXT PRIMARY KEY, index_date TEXT NOT NULL,"
        "dx_code TEXT NOT NULL)"
    )
    conn.execute("CREATE TABLE scan_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO scan_state VALUES ('scan_complete', '0')")
    conn.commit()
    return conn


def save_chunk(conn: sqlite3.Connection, events: pd.DataFrame) -> None:
    if events.empty:
        return
    events = events.sort_values(["patient_id", "date", "code"]).drop_duplicates(
        "patient_id", keep="first"
    )
    rows = list(events[["patient_id", "date", "code"]].itertuples(index=False, name=None))
    conn.executemany(
        "INSERT INTO first_principal_I63(patient_id,index_date,dx_code) VALUES (?,?,?) "
        "ON CONFLICT(patient_id) DO UPDATE SET "
        "index_date=excluded.index_date, dx_code=excluded.dx_code "
        "WHERE excluded.index_date < first_principal_I63.index_date",
        rows,
    )


def scan(zip_path: Path, private_dir: Path, *, chunk_rows: int = 150000,
         limit_rows: int | None = None) -> dict:
    """Run a bounded smoke test or a full sequential scan.

    limit_rows=None means FULL scan; CLI requires explicit --full-scan.
    Output may contain sensitive patient IDs in a private SQLite database.
    """
    if chunk_rows < 1 or (limit_rows is not None and limit_rows < 1):
        raise ValueError("Chunk and row limits must be positive")
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)
    priv = ensure_private_dir(private_dir)
    partial = priv / "step18_diagnosis_index.partial.sqlite"
    completed = priv / "step18_diagnosis_index.sqlite"
    if completed.exists() or partial.exists():
        raise FileExistsError("Prior Step 18 database exists. Review it before rerunning.")
    counters = {
        "rows_scanned": 0, "in_year_icd10_I63_rows": 0,
        "in_year_icd10_I63_P_rows": 0,
        "in_year_icd10_I63_unknown_principal_rows": 0,
        "qualifying_missing_patient_id_rows": 0,
        "qualifying_invalid_calendar_date_rows": 0,
        "qualifying_rows_retained": 0,
    }
    conn = None
    with ZipFile(zip_path, "r") as zf:
        if SOURCE not in zf.namelist():
            raise ValueError(f"{SOURCE} not present in archive")
        declared = expected_rows(zf)
        conn = init_database(partial)
        try:
            with zf.open(SOURCE, "r") as f:
                reader = pd.read_csv(f, usecols=COLUMNS, dtype="string", chunksize=chunk_rows,
                                     keep_default_na=False, low_memory=False)
                for chunk in reader:
                    if limit_rows is not None:
                        remaining = limit_rows - counters["rows_scanned"]
                        if remaining <= 0:
                            break
                        chunk = chunk.iloc[:remaining]
                    selected, info = choose_principal_I63(chunk)
                    for name in counters:
                        counters[name] += int(info[name])
                    save_chunk(conn, selected)
                    conn.commit()
                    if limit_rows is not None and counters["rows_scanned"] >= limit_rows:
                        break
            if limit_rows is None and declared is not None and counters["rows_scanned"] != declared:
                raise ValueError(
                    "Full diagnosis scan row count differs from ZIP manifest: "
                    f"{counters['rows_scanned']} vs {declared}"
                )
            full = limit_rows is None
            distinct = int(conn.execute("SELECT COUNT(*) FROM first_principal_I63").fetchone()[0])
            first_years = dict(conn.execute(
                "SELECT substr(index_date,1,4), COUNT(*) FROM first_principal_I63 "
                "GROUP BY substr(index_date,1,4)"
            ).fetchall())
            conn.execute(
                "INSERT OR REPLACE INTO scan_state VALUES ('scan_complete', ?)",
                ("1" if full else "0",),
            )
            conn.execute(
                "INSERT OR REPLACE INTO scan_state VALUES ('source_rows_scanned', ?)",
                (str(counters["rows_scanned"]),),
            )
            conn.commit()
        finally:
            conn.close()
    if limit_rows is None:
        partial.replace(completed)
    return {
        "stage": "STEP18_DIAGNOSIS_FIRST_PROVISIONAL_INDEX",
        "source": SOURCE,
        "mode": "full" if limit_rows is None else "bounded_smoke_test",
        "scan_complete": limit_rows is None,
        "declared_total_source_rows": declared,
        "aggregate_counters": counters,
        "distinct_principal_I63_candidate_patients": distinct,
        "candidate_index_year_counts": {str(y): int(v) for y, v in first_years.items()},
        "local_private_database_file": (
            completed.name if limit_rows is None else partial.name),
        "ready_for_imaging_utilization_inference": False,
        "warnings": [
            "2018-2019 first principal ICD-10-CM I63 DIAGNOSIS, not verified first stroke admission.",
            "Source lacks encounter IDs; patient/date linkage is a temporal proxy.",
            "H34.1, ICD-9 and unknown-principal diagnoses excluded pending codebook review.",
            "No demographic age cutoffs or CT eligibility have yet been applied.",
            "Bounded smoke-test output is INCOMPLETE and cannot be used in downstream stages.",
            "Interrupted ZIP scans cannot resume efficiently without re-decompression.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--private-dir", type=Path, required=True,
                   help="Approved owner-only directory outside Git repository")
    choice = p.add_mutually_exclusive_group(required=True)
    choice.add_argument("--limit-rows", type=int, help="Smoke-test first N nonrepresentative rows")
    choice.add_argument("--full-scan", action="store_true", help="Scan all diagnosis source rows")
    p.add_argument("--chunk-rows", type=int, default=150000)
    p.add_argument("--output", type=Path,
                   default=ROOT / "results/phase1/step18_diagnosis_index_audit.json")
    args = p.parse_args()
    report = scan(args.zip, args.private_dir, chunk_rows=args.chunk_rows,
                  limit_rows=None if args.full_scan else args.limit_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Aggregate-only source scan report:", args.output)
    print("Completed full archive scan:", report["scan_complete"])
    print("Index candidate patients:", report["distinct_principal_I63_candidate_patients"])
    print("Patient rows stored ONLY in designated private local SQLite directory.")
    print("NOT a verified stroke admission cohort; imaging analyses remain blocked.")


if __name__ == "__main__":
    main()
