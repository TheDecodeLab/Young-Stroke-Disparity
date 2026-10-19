#!/usr/bin/env python3
"""Step62: checkpointed LOCAL-only provisional young-stroke cohort reconstruction.

One source member per stage. No source data, identifiers, or private SQLite
ever leave the approved workstation. Output is NOT a validated clinical result.
Step45 remains disabled. See docs/STEP62_CHECKPOINTED_COHORT_PIPELINE.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sqlite3
import stat
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "results/phase1/step36_research_metadata_preflight.json"
PRIVATE = ROOT / "results/phase1/full_reconstruction_private/step62_cohort_private"
DB = PRIVATE / "provisional_cohort_LOCAL_ONLY.sqlite"
ACK = "I_CONFIRM_EXISTING_PROTOCOL_PERMITS_LOCAL_COHORT_RECONSTRUCTION"
STAGES = ("diagnosis", "encounter", "patient", "index", "procedure", "report")
SOURCE = ("diagnosis", "encounter", "patient", "procedure")
INPUT_COLUMNS = {
    "diagnosis": {"patient_id", "encounter_id", "code_system", "code", "date",
                  "principal_diagnosis_indicator"},
    "encounter": {"patient_id", "encounter_id", "start_date", "end_date", "type"},
    "patient": {"patient_id", "year_of_birth", "sex", "race", "ethnicity"},
    "procedure": {"patient_id", "encounter_id", "date", "code_system", "code"},
}
CPT = {
    "70450": "CT_HEAD", "70460": "CT_HEAD", "70470": "CT_HEAD",
    "70496": "CTA_HEAD", "70498": "CTA_NECK",
    "70544": "MRA_HEAD", "70545": "MRA_HEAD", "70546": "MRA_HEAD",
    "70547": "MRA_NECK", "70548": "MRA_NECK", "70549": "MRA_NECK",
    "70551": "MRI_BRAIN", "70552": "MRI_BRAIN", "70553": "MRI_BRAIN",
}
COHORTS = ("uniform_18_50", "historical_sex_specific_18_52_54")
START = "20160101"
END = "20241231"
CHUNK = 20000
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS progress(stage TEXT PRIMARY KEY, seen INTEGER NOT NULL, done INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS dx(patient TEXT NOT NULL, encounter TEXT NOT NULL, day TEXT NOT NULL,
 principal INTEGER NOT NULL, PRIMARY KEY(patient,encounter,day));
CREATE INDEX IF NOT EXISTS dx_lookup ON dx(patient,encounter,day);
CREATE TABLE IF NOT EXISTS admission(patient TEXT NOT NULL, encounter TEXT NOT NULL,
 start TEXT NOT NULL, end TEXT NOT NULL, principal INTEGER NOT NULL,
 PRIMARY KEY(patient,encounter));
CREATE INDEX IF NOT EXISTS admission_patient ON admission(patient,start,encounter);
CREATE TABLE IF NOT EXISTS person(patient TEXT PRIMARY KEY, yob INTEGER, sex TEXT NOT NULL,
 race TEXT NOT NULL, ethnicity TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS idx(cohort TEXT NOT NULL, patient TEXT NOT NULL,
 encounter TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL,
 principal INTEGER NOT NULL, PRIMARY KEY(cohort,patient));
CREATE INDEX IF NOT EXISTS idx_enc ON idx(patient,encounter);
CREATE TABLE IF NOT EXISTS image(cohort TEXT NOT NULL, patient TEXT NOT NULL,
 category TEXT NOT NULL, PRIMARY KEY(cohort,patient,category));
CREATE TABLE IF NOT EXISTS audit(cohort TEXT NOT NULL, finding TEXT NOT NULL,
 n INTEGER NOT NULL, PRIMARY KEY(cohort,finding));
"""


def parsedate(value):
    """Accept exact YYYYMMDD or ISO date; return sortable compact string."""
    raw = (value or "").strip()
    if len(raw) == 8 and raw.isascii() and raw.isdigit():
        compact = raw
    elif len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        compact = raw.replace("-", "")
    else:
        return None
    if not compact.isascii() or not compact.isdigit():
        return None
    try:
        date(int(compact[:4]), int(compact[4:6]), int(compact[6:]))
    except ValueError:
        return None
    return compact


def stroke_candidate(system, code):
    """Conservative ICD-10-CM I63.* candidate, with optional I63 parent."""
    import re
    c = (code or "").strip().upper()
    return ((system or "").strip().upper() == "ICD-10-CM"
            and bool(re.fullmatch(r"I63(?:\.[A-Z0-9]{1,5})?", c)))


def age_class(day, yob, sex, cohort):
    """YOB gives an age interval. Never silently include uncertain boundary."""
    if not isinstance(yob, int) or yob < 1900 or yob > int(day[:4]):
        return "unknown_yob"
    low, high = int(day[:4]) - yob - 1, int(day[:4]) - yob
    if cohort == COHORTS[0]:
        upper = 50
    elif cohort == COHORTS[1]:
        normalized = (sex or "").strip().upper()
        upper = 52 if normalized in ("M", "MALE") else (
            54 if normalized in ("F", "FEMALE") else None)
    else:
        raise ValueError("Unknown cohort")
    if upper is None:
        return "unknown_sex"
    if low >= 18 and high <= upper:
        return "definite"
    if high < 18 or low > upper:
        return "excluded"
    return "boundary_uncertain"


def _private_dir(folder=PRIVATE):
    base = (ROOT / "results/phase1/full_reconstruction_private").resolve()
    candidate = Path(folder).expanduser().resolve()
    if base not in candidate.parents or candidate == base:
        raise ValueError("Private stage folder must be in gitignored private results")
    candidate.mkdir(parents=True, exist_ok=True, mode=0o700)
    if candidate.stat().st_mode & 0o077:
        raise PermissionError("Private folder must have mode 0700")
    return candidate


def verified_zip(source, preflight=PREFLIGHT):
    """Return opened ZIP + frozen signature. Caller closes ZIP."""
    prior_bytes = Path(preflight).read_bytes()
    prior = json.loads(prior_bytes)
    if (prior.get("stage") != "STEP36_RESEARCH_METADATA_PREFLIGHT" or
        prior.get("clinical_rows_read") != 0 or
        prior.get("full_clinical_tables_scanned") is not False):
        raise ValueError("Step36 source provenance mismatch")
    z = zipfile.ZipFile(source, "r")
    try:
        members = {}
        for item in z.infolist():
            key = item.filename.replace("\\", "/").split("/")[-1].lower()
            if key in (k + ".csv" for k in SOURCE) and not item.is_dir():
                if key in members:
                    raise ValueError("Duplicate source member")
                members[key] = item
        if set(members) != {k + ".csv" for k in SOURCE}:
            raise ValueError("All four required source members must be present")
        frozen = []
        for name in sorted(members):
            m = members[name]
            expected = prior.get("files", {}).get(name, {})
            if (expected.get("present") is not True
                    or expected.get("uncompressed_bytes") != m.file_size
                    or not INPUT_COLUMNS[name[:-4]].issubset(expected.get("headers", []))):
                raise ValueError("Step36 source member signature mismatch")
            frozen.append((name, m.file_size, m.CRC, tuple(expected["headers"])))
        fingerprint = hashlib.sha256(json.dumps(
            [frozen, hashlib.sha256(prior_bytes).hexdigest(), START, END, "STEP62_V1"],
            sort_keys=True).encode()).hexdigest()
        return z, members, prior, fingerprint
    except Exception:
        z.close()
        raise


def connection(folder):
    path = folder / DB.name
    if path.is_symlink():
        raise ValueError("Private DB must not be symlink")
    # SQLite opens with owner-only mode under restrictive process umask.
    old = os.umask(0o077)
    try:
        db = sqlite3.connect(str(path), timeout=60)
    finally:
        os.umask(old)
    os.chmod(str(path), stat.S_IRUSR | stat.S_IWUSR)
    db.execute("PRAGMA journal_mode=DELETE")
    db.execute("PRAGMA synchronous=FULL")
    db.executescript(SCHEMA)
    db.commit()
    return db


def progress(db, stage):
    value = db.execute("SELECT seen,done FROM progress WHERE stage=?", (stage,)).fetchone()
    return value if value is not None else (0, 0)


def done(db, stage):
    return progress(db, stage)[1] == 1


def _stage_order(db, stage):
    if done(db, stage):
        raise ValueError("Stage already completed; no rerun")
    for predecessor in STAGES[:STAGES.index(stage)]:
        if not done(db, predecessor):
            raise ValueError("Run prior stage first: " + predecessor)


def _source_row(db, stage, row):
    p = (row.get("patient_id") or "").strip()
    e = (row.get("encounter_id") or "").strip()
    if stage == "diagnosis":
        if not p or not e or not stroke_candidate(row.get("code_system"), row.get("code")):
            return
        d = parsedate(row.get("date"))
        if d is None or not START <= d <= END:
            return
        principal = int((row.get("principal_diagnosis_indicator") or "").strip().upper() == "P")
        db.execute("""INSERT INTO dx VALUES(?,?,?,?)
          ON CONFLICT(patient,encounter,day)
          DO UPDATE SET principal=MAX(principal,excluded.principal)""", (p, e, d, principal))
    elif stage == "encounter":
        if not p or not e or (row.get("type") or "").strip().upper() != "IMP":
            return
        start = parsedate(row.get("start_date"))
        end = parsedate(row.get("end_date"))
        if start is None or not START <= start <= END or end is None or end < start:
            return  # Missing end or reversed span is unassessable, never imaging-negative.
        flag = db.execute("""SELECT MAX(principal) FROM dx
          WHERE patient=? AND encounter=? AND day>=? AND day<=?""",
          (p, e, start, end)).fetchone()[0]
        if flag is not None:
            previous = db.execute(
                "SELECT start,end FROM admission WHERE patient=? AND encounter=?",
                (p, e)).fetchone()
            if previous is not None and previous != (start, end):
                raise ValueError("Conflicting duplicate qualifying inpatient encounter key")
            db.execute("""INSERT INTO admission VALUES(?,?,?,?,?)
              ON CONFLICT(patient,encounter) DO UPDATE SET
              principal=MAX(principal,excluded.principal)""",
              (p, e, start, end, int(flag)))
    elif stage == "patient":
        if not p or db.execute("SELECT 1 FROM admission WHERE patient=? LIMIT 1", (p,)).fetchone() is None:
            return
        val = (row.get("year_of_birth") or "").strip()
        yob = int(val) if len(val) == 4 and val.isascii() and val.isdigit() else None
        demographics = (yob, (row.get("sex") or "").strip(),
                        (row.get("race") or "").strip(),
                        (row.get("ethnicity") or "").strip())
        previous = db.execute(
            "SELECT yob,sex,race,ethnicity FROM person WHERE patient=?", (p,)).fetchone()
        if previous is not None and previous != demographics:
            raise ValueError("Conflicting duplicate patient demographics")
        db.execute("INSERT OR IGNORE INTO person VALUES(?,?,?,?,?)", (p,) + demographics)
    elif stage == "procedure":
        if not p or not e or (row.get("code_system") or "").strip().upper() != "CPT":
            return
        category = CPT.get((row.get("code") or "").strip())
        if category is None:
            return
        day = parsedate(row.get("date"))
        if day is None:
            return
        for cohort, start, end in db.execute(
          "SELECT cohort,start,end FROM idx WHERE patient=? AND encounter=?", (p, e)):
            if start <= day <= end:
                db.execute("INSERT OR IGNORE INTO image VALUES(?,?,?)", (cohort, p, category))
    else:
        raise ValueError("Unknown source stage")


def _stream_stage(db, z, member, preflight, stage, chunk=CHUNK, stop_after=None):
    if chunk < 1 or chunk > 100000:
        raise ValueError("Chunk size must be 1..100000")
    expected = preflight.get("relevant_manifest_counts", {}).get(stage+".csv", {}).get("row_count")
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
        raise ValueError("Step36 whole-table manifest count is required")
    skipped, _ = progress(db, stage)
    if skipped > expected:
        raise ValueError("Checkpoint exceeds declared source row count")
    with z.open(member, "r") as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as txt:
        reader = csv.DictReader(txt)
        if reader.fieldnames != preflight["files"][stage+".csv"]["headers"]:
            raise ValueError("CSV header differs from Step36")
        for _ in range(skipped):
            if next(reader, None) is None:
                raise ValueError("Source became shorter than checkpoint")
        rows = skipped
        while True:
            batch = []
            for _ in range(chunk):
                row = next(reader, None)
                if row is None:
                    break
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("Malformed CSV source row")
                batch.append(row)
            if not batch:
                break
            with db:
                for record in batch:
                    _source_row(db, stage, record)
                rows += len(batch)
                db.execute("""INSERT INTO progress VALUES(?,?,0)
                  ON CONFLICT(stage) DO UPDATE SET seen=excluded.seen,done=0""",
                  (stage, rows))
            if stop_after is not None and rows >= stop_after:
                return False
        if rows != expected:
            raise ValueError("Source row count does not match Step36 manifest")
        with db:
            db.execute("""INSERT INTO progress VALUES(?,?,1)
                ON CONFLICT(stage) DO UPDATE SET seen=excluded.seen,done=1""",
                (stage, rows))
    return True


def _audit(db, cohort, finding):
    db.execute("""INSERT INTO audit VALUES(?,?,1)
      ON CONFLICT(cohort,finding) DO UPDATE SET n=n+1""", (cohort, finding))


def _index(db):
    """Earliest definitely-age-eligible index per patient and cohort.

    For competing same-day admissions, place patient on hold (no arbitrary
    encounter_id tie break). Uncertain YOB boundaries are not silently included.
    """
    cur = db.execute("""SELECT a.patient,a.encounter,a.start,a.end,a.principal,
                               p.yob,p.sex FROM admission a
                        LEFT JOIN person p ON p.patient=a.patient
                        ORDER BY a.patient,a.start,a.encounter""")
    prior = None
    first = {c: None for c in COHORTS}
    tie = {c: False for c in COHORTS}
    def flush():
        if prior is None:
            return
        for c in COHORTS:
            result = first[c]
            if result is not None and not tie[c]:
                db.execute("INSERT INTO idx VALUES(?,?,?,?,?,?)",
                           (c, prior, result[0], result[1], result[2], result[3]))
            elif result is not None and tie[c]:
                _audit(db, c, "patient_held_competing_same_day_index_encounters")
    with db:
        for patient, encounter, start, end, principal, yob, sex in cur:
            if patient != prior:
                flush()
                prior = patient
                first = {c: None for c in COHORTS}
                tie = {c: False for c in COHORTS}
            for cohort in COHORTS:
                age_status = age_class(start, yob, sex, cohort)
                _audit(db, cohort, "candidate_admission_age_" + age_status)
                if age_status != "definite":
                    continue
                selected = first[cohort]
                if selected is None:
                    first[cohort] = (encounter, start, end, principal)
                elif selected[1] == start:
                    tie[cohort] = True
        flush()
        db.execute("INSERT INTO progress VALUES('index',0,1)")


def _report(db, folder):
    if (folder / "aggregate_review_LOCAL_ONLY.json").exists():
        raise FileExistsError("Report already exists, refusing overwrite")
    cohorts = {}
    for cohort in COHORTS:
        n = db.execute("SELECT COUNT(*) FROM idx WHERE cohort=?", (cohort,)).fetchone()[0]
        rows = db.execute("""SELECT substr(start,1,4),COUNT(*),SUM(principal)
              FROM idx WHERE cohort=? GROUP BY substr(start,1,4) ORDER BY 1""",
              (cohort,)).fetchall()
        images = db.execute("""SELECT i.category,COUNT(*)
              FROM image i WHERE i.cohort=? GROUP BY i.category ORDER BY i.category""",
              (cohort,)).fetchall()
        audits = dict(db.execute(
            "SELECT finding,n FROM audit WHERE cohort=? ORDER BY finding", (cohort,)))
        cohorts[cohort] = {"indexed_patients_not_validated": n,
            "candidate_admission_age_QA_NOT_patient_denominators": audits,
            "by_start_year": {year: {"index_cases": count, "with_P_label": principal or 0}
                              for year, count, principal in rows},
            "primary_same_IMP_CPT14_code_capture_counts_NOT_performed_scans": dict(images)}
    out = {
        "stage": "STEP62_PROVISIONAL_PRIVATE_RECONSTRUCTION",
        "source_year_start": 2016, "source_year_end_PROVISIONAL": 2024,
        "stroke_ascertainment": "ICD-10-CM_I63_family_BROAD_with_P_flag_unvalidated",
        "index_rule": "earliest definitely_eligible hospitalization_with_unambiguous_start",
        "index_missing_end": "excluded_as_unassessable",
        "unresolved_age_boundary": "excluded_pending_YOB_policy",
        "imaging": "documented_CPT14_on_same_IMP_encounter_within_stay",
        "imaging_completion_verified": False, "site_HCO_linkage_verified": False,
        "ED_date_only_sensitivity_included": False,
        "race_ethnicity_disparities_computed": False,
        "cohorts": cohorts,
        "private_index_source_counts_NOT_independent_patients": {
            "I63_candidate_patient_encounter_dates": db.execute(
                "SELECT COUNT(*) FROM dx").fetchone()[0],
            "matched_IMP_encounter_rows": db.execute(
                "SELECT COUNT(*) FROM admission").fetchone()[0],
            "matched_patient_demographic_rows": db.execute(
                "SELECT COUNT(*) FROM person").fetchone()[0],
        },
        "external_sharing_requires_review": True,
    }
    path = folder / "aggregate_review_LOCAL_ONLY.json"
    with path.open("x", encoding="utf-8") as handle:
        os.chmod(path, 0o600)
        json.dump(out, handle, sort_keys=True, indent=2)
        handle.write("\n")
    with db:
        db.execute("INSERT INTO progress VALUES('report',0,1)")
    return path


def run(source, stage, preflight=PREFLIGHT, folder=PRIVATE,
        chunk=CHUNK, stop_after=None):
    if stage not in STAGES:
        raise ValueError("Unknown stage")
    folder = _private_dir(folder)
    z, members, prior, fingerprint = verified_zip(source, preflight)
    try:
        db = connection(folder)
        try:
            key = db.execute("SELECT value FROM meta WHERE key='source'").fetchone()
            if key and key[0] != fingerprint:
                raise ValueError("Source/preflight/year policy changed since checkpoint")
            if not key:
                with db:
                    db.execute("INSERT INTO meta VALUES('source',?)", (fingerprint,))
            _stage_order(db, stage)
            if stage in SOURCE:
                completed = _stream_stage(db, z, members[stage+".csv"], prior,
                                          stage, chunk=chunk, stop_after=stop_after)
            elif stage == "index":
                _index(db)
                completed = True
            else:
                _report(db, folder)
                completed = True
            return {"stage": stage, "complete": completed,
                    "processed_rows": progress(db, stage)[0],
                    "private_output_directory": str(folder)}
        finally:
            db.close()
    finally:
        z.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--acknowledge", required=True)
    parser.add_argument("--chunk", type=int, default=CHUNK)
    args = parser.parse_args(argv)
    if args.acknowledge != ACK:
        parser.error("Explicit existing approved local cohort processing acknowledgment required")
    result = run(args.zip, args.stage, chunk=args.chunk)
    print("Private Step62 stage:", result["stage"])
    print("Complete:", result["complete"], "rows read:", result["processed_rows"])
    print("Private working directory:", result["private_output_directory"])
    print("Provisional cohort and recorded-code data only. Never commit private results.")


if __name__ == "__main__":
    main()
