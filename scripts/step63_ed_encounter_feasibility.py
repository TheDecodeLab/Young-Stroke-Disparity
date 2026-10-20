#!/usr/bin/env python3
"""Step63: LOCAL-only, checkpointed ED-to-index encounter feasibility.

This stage DOES NOT link ED procedures, validate same-hospital transfers,
prove imaging delivery, or estimate disparities. Never upload its SQLite DB.
Requires a completed Step62 and unchanged ZIP/preflight. Python 3.9.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile

try:
    from scripts import step62_checkpointed_cohort as s62
except ModuleNotFoundError:
    # python scripts/step63_ed_encounter_feasibility.py
    import step62_checkpointed_cohort as s62

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "results/phase1/full_reconstruction_private/step63_ed_sensitivity_private"
DATABASE = "step63_ed_feasibility_LOCAL_ONLY.sqlite"
REPORT = "step63_ed_feasibility_LOCAL_ONLY.json"
STAGES = ("encounter", "link")
VERSION = "STEP63_ED_FEASIBILITY_V1"
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS progress(stage TEXT PRIMARY KEY, seen INTEGER NOT NULL, done INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS subject(patient TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS idx(cohort TEXT NOT NULL,patient TEXT NOT NULL,encounter TEXT NOT NULL,
 start TEXT NOT NULL,end TEXT NOT NULL,principal INTEGER NOT NULL,
 PRIMARY KEY(cohort,patient));
CREATE TABLE IF NOT EXISTS evt(patient TEXT NOT NULL,encounter TEXT NOT NULL,
 kind TEXT NOT NULL,start TEXT NOT NULL,end TEXT NOT NULL,
 derived TEXT NOT NULL,start_derived TEXT NOT NULL,end_derived TEXT NOT NULL,
 PRIMARY KEY(patient,encounter));
CREATE INDEX IF NOT EXISTS evt_start ON evt(patient,kind,start);
CREATE INDEX IF NOT EXISTS evt_end ON evt(patient,kind,end);
CREATE TABLE IF NOT EXISTS ambiguous(patient TEXT NOT NULL,encounter TEXT NOT NULL,
 PRIMARY KEY(patient,encounter));
CREATE TABLE IF NOT EXISTS pair(patient TEXT NOT NULL,ed TEXT NOT NULL,imp TEXT NOT NULL,
 PRIMARY KEY(patient,ed,imp));
CREATE INDEX IF NOT EXISTS pair_imp ON pair(patient,imp);
CREATE TABLE IF NOT EXISTS linked(cohort TEXT NOT NULL,patient TEXT NOT NULL,
 ed TEXT NOT NULL,imp TEXT NOT NULL,ed_start TEXT NOT NULL,ed_end TEXT NOT NULL,
 PRIMARY KEY(cohort,patient));
"""


def _iso(raw):
    compact = s62.parsedate(raw)
    return None if compact is None else (
        compact[:4] + "-" + compact[4:6] + "-" + compact[6:8])


def _private(folder):
    # Use the existing Step62 guard. Nothing is placed outside ignored results.
    return s62._private_dir(folder)


def _open_db(folder):
    target = folder / DATABASE
    if target.is_symlink():
        raise ValueError("Step63 database must not be a symlink")
    old = os.umask(0o077)
    try:
        db = sqlite3.connect(str(target), timeout=60)
    finally:
        os.umask(old)
    os.chmod(str(target), stat.S_IRUSR | stat.S_IWUSR)
    db.execute("PRAGMA journal_mode=DELETE")
    db.execute("PRAGMA synchronous=FULL")
    db.executescript(SCHEMA)
    return db


def _source_snapshot(step62_folder):
    path = Path(step62_folder).resolve() / s62.DB.name
    if not path.is_file() or path.is_symlink():
        raise ValueError("Completed Step62 private SQLite database is required")
    st = path.stat()
    with sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True) as src:
        status = dict(src.execute("SELECT stage,done FROM progress"))
        if any(status.get(stage) != 1 for stage in s62.STAGES):
            raise ValueError("Step62 must be completed through report")
        signature = json.dumps({
            "step62_db_path": str(path),
            "size": st.st_size, "mtime_ns": st.st_mtime_ns,
            "source_meta": list(src.execute("SELECT key,value FROM meta ORDER BY key")),
            "complete_stages": sorted(status.items()),
        }, sort_keys=True)
    return path, hashlib.sha256(signature.encode()).hexdigest()


def _bootstrap(db, source_path, frozen):
    stored = db.execute("SELECT v FROM meta WHERE k='step62_snapshot'").fetchone()
    if stored is not None:
        if stored[0] != frozen:
            raise ValueError("Step62 source DB changed after Step63 snapshot")
        return
    if db.execute("SELECT COUNT(*) FROM idx").fetchone()[0]:
        raise ValueError("Untracked Step63 staging state")
    with sqlite3.connect("file:" + str(source_path) + "?mode=ro", uri=True) as src:
        with db:
            db.executemany("INSERT INTO idx VALUES(?,?,?,?,?,?)",
                src.execute("SELECT cohort,patient,encounter,start,end,principal FROM idx"))
            db.execute("INSERT INTO subject SELECT DISTINCT patient FROM idx")
            db.execute("INSERT INTO meta VALUES('step62_snapshot',?)", (frozen,))


def _assert_zip(db, frozen):
    row = db.execute("SELECT v FROM meta WHERE k='zip_fingerprint'").fetchone()
    if row is None:
        with db:
            db.execute("INSERT INTO meta VALUES('zip_fingerprint',?)", (frozen,))
            db.execute("INSERT INTO meta VALUES('policy',?)", (VERSION,))
    elif row[0] != frozen:
        raise ValueError("Step63 source ZIP/preflight/policy fingerprint changed")
    if db.execute("SELECT v FROM meta WHERE k='policy'").fetchone()[0] != VERSION:
        raise ValueError("Step63 algorithm policy changed; manual review required")


def _progress(db, stage):
    return db.execute("SELECT seen,done FROM progress WHERE stage=?",
                      (stage,)).fetchone() or (0, 0)


def _record(db, row, subjects):
    p = (row.get("patient_id") or "").strip()
    if p not in subjects:
        return
    e = (row.get("encounter_id") or "").strip()
    kind = (row.get("type") or "").strip().upper()
    if not e or kind not in ("EMER", "IMP"):
        return
    if db.execute("SELECT 1 FROM ambiguous WHERE patient=? AND encounter=?",
                  (p,e)).fetchone():
        return
    start = _iso(row.get("start_date"))
    end = _iso(row.get("end_date"))
    if start is None or end is None or end < start:
        # Invalid duplicate date cannot be treated as a valid alternate stay.
        db.execute("INSERT OR IGNORE INTO ambiguous VALUES(?,?)", (p,e))
        db.execute("DELETE FROM evt WHERE patient=? AND encounter=?", (p,e))
        return
    flags = tuple((row.get(key) or "").strip()[:80] for key in (
        "derived_by_TriNetX","start_date_derived_by_TriNetX",
        "end_date_derived_by_TriNetX"))
    prior = db.execute(
        "SELECT kind,start,end,derived,start_derived,end_derived FROM evt "
        "WHERE patient=? AND encounter=?", (p,e)).fetchone()
    if prior is not None:
        if prior[:3] != (kind,start,end):
            db.execute("INSERT OR IGNORE INTO ambiguous VALUES(?,?)", (p,e))
            db.execute("DELETE FROM evt WHERE patient=? AND encounter=?", (p,e))
        elif prior[3:] != flags:
            # Preserve discordant provenance flags as indeterminate rather
            # than adopting whichever duplicate row appears first.
            db.execute("UPDATE evt SET derived='MIXED',start_derived='MIXED',"
                       "end_derived='MIXED' WHERE patient=? AND encounter=?", (p,e))
        return
    db.execute("INSERT INTO evt VALUES(?,?,?,?,?,?,?,?)",
               (p,e,kind,start,end) + flags)


def _scan(db, archive, member, preflight, chunk=20000, stop_after=None):
    if not 1 <= chunk <= 100000:
        raise ValueError("Chunk must be between 1 and 100000")
    expected = preflight["relevant_manifest_counts"]["encounter.csv"]["row_count"]
    seen, complete = _progress(db, "encounter")
    if complete:
        raise ValueError("Stage already completed; no rerun")
    if seen > expected:
        raise ValueError("Checkpoint exceeds source manifest")
    subjects = {p for (p,) in db.execute("SELECT patient FROM subject")}
    with archive.open(member, "r") as raw, io.TextIOWrapper(
            raw, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != preflight["files"]["encounter.csv"]["headers"]:
            raise ValueError("Encounter headers differ from frozen preflight")
        for _ in range(seen):
            if next(reader, None) is None:
                raise ValueError("Encounter source shorter than saved checkpoint")
        while True:
            batch = []
            for _ in range(chunk):
                rec = next(reader, None)
                if rec is None:
                    break
                if None in rec or any(v is None for v in rec.values()):
                    raise ValueError("Malformed encounter source row")
                batch.append(rec)
            if not batch:
                break
            with db:
                for rec in batch:
                    _record(db, rec, subjects)
                seen += len(batch)
                db.execute("""INSERT INTO progress VALUES('encounter',?,0)
                  ON CONFLICT(stage) DO UPDATE SET seen=excluded.seen,done=0""",
                  (seen,))
            if stop_after is not None and seen >= stop_after:
                return False
    if seen != expected:
        raise ValueError("Encounter rows do not reconcile with Step36 manifest")
    with db:
        db.execute("""INSERT INTO progress VALUES('encounter',?,1)
          ON CONFLICT(stage) DO UPDATE SET seen=excluded.seen,done=1""",
          (seen,))
    return True


def _link(db):
    if _progress(db, "encounter")[1] != 1:
        raise ValueError("Run prior stage first: encounter")
    if _progress(db, "link")[1]:
        raise ValueError("Stage already completed; no rerun")
    # Step62's selected IMP must still be a well-formed, unambiguous row.
    invalid = db.execute("""SELECT COUNT(*) FROM idx i
      LEFT JOIN evt e ON e.patient=i.patient AND e.encounter=i.encounter
      WHERE e.patient IS NULL OR e.kind!='IMP' OR
            e.start!=substr(i.start,1,4)||'-'||substr(i.start,5,2)||'-'||substr(i.start,7,2)
         OR e.end!=substr(i.end,1,4)||'-'||substr(i.end,5,2)||'-'||substr(i.end,7,2)
    """).fetchone()[0]
    if invalid:
        raise ValueError(
            "Step63 identified " + str(invalid) +
            " index rows with missing/conflicting IMP spans. Review source "
            "encounter semantics before ED linkage; no rows were linked.")
    with db:
        db.execute("""INSERT INTO pair
          SELECT ed.patient,ed.encounter,ip.encounter
          FROM evt ed
          JOIN evt ip ON ip.patient=ed.patient AND ip.kind='IMP'
                       AND ip.start>=ed.end AND ip.start<=date(ed.end,'+1 day')
          WHERE ed.kind='EMER' AND ed.encounter!=ip.encounter""")
        # Two-way uniqueness is evaluated among ALL IMPs of indexed patients,
        # not merely the selected index IMPs and not conditional on imaging.
        db.execute("""INSERT INTO linked
          SELECT i.cohort,i.patient,p.ed,p.imp,e.start,e.end
          FROM idx i
          JOIN pair p ON p.patient=i.patient AND p.imp=i.encounter
          JOIN evt e ON e.patient=p.patient AND e.encounter=p.ed
          WHERE (SELECT COUNT(*) FROM pair q
                 WHERE q.patient=p.patient AND q.ed=p.ed)=1
            AND (SELECT COUNT(*) FROM pair q
                 WHERE q.patient=p.patient AND q.imp=p.imp)=1""")
        db.execute("INSERT INTO progress VALUES('link',0,1)")
    return True


def _report(db, folder):
    counts = {}
    for cohort in s62.COHORTS:
        n = db.execute("SELECT COUNT(*) FROM idx WHERE cohort=?", (cohort,)).fetchone()[0]
        linked = db.execute(
            "SELECT COUNT(*) FROM linked WHERE cohort=?", (cohort,)).fetchone()[0]
        year_rows = list(db.execute("""
          SELECT substr(i.start,1,4),COUNT(*),
            SUM(CASE WHEN l.patient IS NOT NULL THEN 1 ELSE 0 END)
          FROM idx i LEFT JOIN linked l
             ON i.cohort=l.cohort AND i.patient=l.patient
          WHERE i.cohort=? GROUP BY substr(i.start,1,4)
          ORDER BY 1""", (cohort,)))
        counts[cohort] = {
            "step62_indexed_patients_NOT_validated": n,
            "uniquely_linked_ED_patients_date_only": linked,
            "by_year_NOT_hospital_confirmed": {
                y: {"indexed": total, "date_only_unique_ED": linked_year or 0}
                for y, total, linked_year in year_rows},
        }
    record = {
        "stage": VERSION, "ED_procedure_scanned": False,
        "performed_imaging_verified": False, "same_HCO_verified": False,
        "date_only_lookback_days": [0,1],
        "source_id_as_HCO": False,
        "all_IMP_competitors_examined_for_indexed_patients": True,
        "source_type_other_than_EMER_IMP_collisions_not_exhaustively_checked": True,
        "duplicate_dates_quarantined": True,
        "not_for_public_release_without_disclosure_review": True,
        "indexed_cohorts": counts,
        "distinct_patients_examined": db.execute(
            "SELECT COUNT(*) FROM subject").fetchone()[0],
        "unique_candidate_pair_rows": db.execute(
            "SELECT COUNT(*) FROM pair").fetchone()[0],
        "quarantined_patient_encounter_keys": db.execute(
            "SELECT COUNT(*) FROM ambiguous").fetchone()[0],
        "event_records_for_indexed_patients": {
            kind: db.execute("SELECT COUNT(*) FROM evt WHERE kind=?",
                             (kind,)).fetchone()[0]
            for kind in ("EMER","IMP")},
        "interpretation": "Date-only uniqueness among candidate EMER-to-IMP "
           "matches, never proof of same-hospital transfer or ED imaging.",
    }
    dest = folder / REPORT
    if dest.exists():
        raise FileExistsError("Step63 report exists; refusing overwrite")
    fd, temp = tempfile.mkstemp(prefix=".step63_", dir=str(folder))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, sort_keys=True)
            f.write("\n")
        os.chmod(temp, 0o600)
        os.link(temp, dest)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return record


def run(archive_path, stage, preflight=s62.PREFLIGHT,
        step62_folder=s62.PRIVATE, folder=PRIVATE,
        chunk=20000, stop_after=None):
    if stage not in STAGES:
        raise ValueError("Stage must be encounter or link")
    folder = _private(folder)
    with s62.single_writer(folder):
        source_path, frozen_step62 = _source_snapshot(step62_folder)
        archive, members, prior, frozen_zip = s62.verified_zip(
            archive_path, preflight)
        try:
            db = _open_db(folder)
            try:
                _bootstrap(db, source_path, frozen_step62)
                _assert_zip(db, frozen_zip)
                if _progress(db, stage)[1]:
                    # Linkage rows may have committed just before a crash in
                    # report creation. Recover only that missing LOCAL ONLY
                    # aggregate without touching the finished link table.
                    if stage == "link" and not (folder / REPORT).exists():
                        _report(db, folder)
                        return {"stage": stage, "complete": True,
                                "processed_rows": _progress(db, stage)[0],
                                "quarantined_keys_LOCAL_ONLY": db.execute(
                                    "SELECT COUNT(*) FROM ambiguous").fetchone()[0],
                                "linked_patient_cohort_rows_LOCAL_ONLY": db.execute(
                                    "SELECT COUNT(*) FROM linked").fetchone()[0],
                                "private_directory": str(folder)}
                    raise ValueError("Stage already completed; no rerun")
                if stage == "encounter":
                    complete = _scan(db, archive, members["encounter.csv"],
                                     prior, chunk, stop_after)
                else:
                    complete = _link(db)
                    _report(db, folder)
                return {"stage": stage, "complete": complete,
                        "processed_rows": _progress(db, stage)[0],
                        "quarantined_keys_LOCAL_ONLY": db.execute(
                            "SELECT COUNT(*) FROM ambiguous").fetchone()[0],
                        "linked_patient_cohort_rows_LOCAL_ONLY": db.execute(
                            "SELECT COUNT(*) FROM linked").fetchone()[0],
                        "private_directory": str(folder)}
            finally:
                db.close()
        finally:
            archive.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--acknowledge", required=True)
    parser.add_argument("--chunk", type=int, default=20000)
    args = parser.parse_args(argv)
    if args.acknowledge != s62.ACK:
        parser.error("Existing approved local cohort-processing attestation required")
    result = run(args.zip, args.stage, chunk=args.chunk)
    print("Step63 ED encounter feasibility:", result["stage"])
    print("Complete:", result["complete"], "source rows read:", result["processed_rows"])
    print("Private directory:", result["private_directory"])
    print("Quarantined encounter keys:", result["quarantined_keys_LOCAL_ONLY"])
    if args.stage == "link":
        print("Unique ED link memberships across cohorts:",
              result["linked_patient_cohort_rows_LOCAL_ONLY"])
        print("LOCAL ONLY aggregate report:", result["private_directory"] + "/" + REPORT)
    print("Date-only study feasibility. No same-hospital or imaging validation.")


if __name__ == "__main__":
    main()
