#!/usr/bin/env python3
"""Step65: LOCAL-ONLY, no-rescan ED/index date provenance quality audit.

Reads completed Step62/Step63 SQLite databases read-only. No source ZIP
access, mutation, row-level outputs, or implicit approval to share results.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64

FLAGS = ("derived", "start_derived", "end_derived")
STATUSES = ("T", "F", "MIXED", "OTHER")
ROLES = ("INDEX_IMP", "LINKED_ED")


def aggregate(db, by_year=False):
    """Summarize only indexed IMP or linked ED records, without patient IDs."""
    # IDs are used within the local SQL join, never selected to Python.
    cols = ("role,cohort,principal,year" if by_year
            else "role,cohort,principal")
    terms = ["COUNT(*) AS n", "SUM(missing) AS missing"]
    for flag in FLAGS:
        for status in STATUSES:
            if status == "OTHER":
                condition = ("UPPER(TRIM(COALESCE(" + flag + ",''))) NOT IN "
                             "('T','F','MIXED')")
            else:
                condition = ("UPPER(TRIM(COALESCE(" + flag + ",'')))='" +
                             status + "'")
            terms.append("SUM(CASE WHEN missing=0 AND " + condition +
                         " THEN 1 ELSE 0 END) AS " + flag + "_" + status)
    sql = """
    WITH records AS (
      SELECT 'INDEX_IMP' role, i.cohort, i.principal,
             substr(i.start,1,4) AS year,
             CASE WHEN e.patient IS NULL THEN 1 ELSE 0 END AS missing,
             e.derived,e.start_derived,e.end_derived
      FROM main.idx i
      LEFT JOIN main.evt e ON e.patient=i.patient AND e.encounter=i.encounter
      UNION ALL
      SELECT 'LINKED_ED' role,l.cohort,i.principal,
             substr(i.start,1,4) AS year,
             CASE WHEN e.patient IS NULL THEN 1 ELSE 0 END AS missing,
             e.derived,e.start_derived,e.end_derived
      FROM main.linked l
      JOIN main.idx i ON i.cohort=l.cohort AND i.patient=l.patient
      LEFT JOIN main.evt e ON e.patient=l.patient AND e.encounter=l.ed
    )
    SELECT %s,%s FROM records
    GROUP BY %s ORDER BY %s
    """ % (cols, ",".join(terms), cols, cols)
    result = []
    for row in db.execute(sql):
        prefix = 4 if by_year else 3
        keys = ("role","cohort","P","year") if by_year else ("role","cohort","P")
        values = dict(zip(keys,row[:prefix]))
        values.update(zip(("n","missing") + tuple(
            f + "_" + status for f in FLAGS for status in STATUSES),
            (int(v or 0) for v in row[prefix:])))
        for flag in FLAGS:
            total = sum(values[flag+"_"+status] for status in STATUSES)
            if total + values["missing"] != values["n"]:
                raise AssertionError("Derived-field status tally did not reconcile")
        result.append(values)
    if not result:
        raise ValueError("No date-provenance aggregate rows available")
    return result


def display(rows):
    print("STEP65 read-only encounter-date derivation audit")
    print("Counts are cohort memberships; overlapping age cohorts are not additive.")
    print("T/F reflect legacy TriNetX dictionary semantics, not verified here.")
    print("No linked ED implies neither absent emergency care nor absent imaging.")
    print("No raw identifiers or private rows are emitted. LOCAL ONLY.")
    for row in rows:
        group = (row["role"], row["cohort"], "P="+str(row["P"]))
        if "year" in row:
            group += (row["year"],)
        if row["n"] < 11:
            print(group, "SUPPRESSED: n<11")
            continue
        print(group, "n", row["n"], "missing_source_event", row["missing"])
        for f in FLAGS:
            print(" ", f, "T", row[f+"_T"], "F", row[f+"_F"],
                  "MIXED", row[f+"_MIXED"], "OTHER_OR_BLANK", row[f+"_OTHER"])
    print("Disclose externally only with institutional authorization.")


def main():
    raw62 = s62.PRIVATE / s62.DB.name
    raw63 = s63.PRIVATE / s63.DATABASE
    if raw62.is_symlink() or raw63.is_symlink():
        raise ValueError("Private SQLite paths cannot be symlinks")
    db62 = raw62.resolve()
    db63 = raw63.resolve()
    if not db62.is_file() or not db63.is_file():
        raise FileNotFoundError("Completed Step62/Step63 private SQLite DBs required")
    with sqlite3.connect("file:" + str(db63) + "?mode=ro", uri=True) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:" + str(db62) + "?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,db62,db63)
        print("BY COHORT AND P LABEL")
        display(aggregate(db,by_year=False))
        print("\nBY YEAR (INDEX IMP AND LINKED ED)")
        display(aggregate(db,by_year=True))


if __name__ == "__main__":
    main()
