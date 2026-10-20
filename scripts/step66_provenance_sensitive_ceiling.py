#!/usr/bin/env python3
"""Step66 LOCAL-ONLY: ED-link provenance-sensitive ceiling; NO source ZIP scan.

Compare Step64's upper bound with subsets whose linking dates are directly
sourced (flag F), and same-day vs next-day links. This is theoretical
CODE-CAPTURE improvement, not performed imaging or verified hospital transfer.
"""
from __future__ import annotations

import sqlite3

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64

MODES = (
    "ALL_UNIQUE",
    "CRITICAL_DATES_SOURCE_FLAG_F",
    "ALL_ED_DATES_SOURCE_FLAG_F",
    "CRITICAL_F_SAME_DAY",
    "CRITICAL_F_NEXT_DAY",
)


def analyze(db):
    """Fast two-pass cohort/ED aggregates; no patient IDs leave SQLite.

    First count baseline imaging via indexed EXISTS against the Step62
    primary-key image table. Then inspect date provenance ONLY for frozen
    Step63 linked ED rows (a much smaller subset). Do not reselect links.
    """
    # Every Step63 linked row must correspond to an existing index and
    # the originally frozen ED/IMP event dates. Refuse silent row loss.
    damaged = db.execute("""
        SELECT COUNT(*) FROM main.linked l
        LEFT JOIN main.idx i ON i.cohort=l.cohort AND i.patient=l.patient
        LEFT JOIN main.evt ed
          ON ed.patient=l.patient AND ed.encounter=l.ed
        LEFT JOIN main.evt ip
          ON ip.patient=l.patient AND ip.encounter=l.imp
        WHERE i.patient IS NULL OR ed.patient IS NULL OR ip.patient IS NULL
          OR l.imp!=i.encounter OR ed.kind!='EMER' OR ip.kind!='IMP'
          OR ed.end<ed.start OR ip.end<ip.start
          OR ed.start!=l.ed_start OR ed.end!=l.ed_end
          OR ip.start!=substr(i.start,1,4)||'-'||substr(i.start,5,2)||'-'||substr(i.start,7,2)
          OR ip.end!=substr(i.end,1,4)||'-'||substr(i.end,5,2)||'-'||substr(i.end,7,2)
    """).fetchone()[0]
    if damaged:
        raise ValueError("Frozen Step63 ED/IMP event or linkage mismatch")

    # Indexed denominator and original inpatient imaging use all Step62
    # cohort members, including those unassessable for ED linkage.
    baseline_query = """
        SELECT i.cohort,substr(i.start,1,4),i.principal,COUNT(*),
               SUM(CASE WHEN EXISTS(
                 SELECT 1 FROM baseline.image im
                 WHERE im.cohort=i.cohort AND im.patient=i.patient
               ) THEN 1 ELSE 0 END)
        FROM main.idx i
        GROUP BY i.cohort,substr(i.start,1,4),i.principal
        ORDER BY i.cohort,substr(i.start,1,4),i.principal
    """
    rows = {}
    for cohort, year, principal, indexed, inpatient_any in db.execute(
            baseline_query):
        rows[(cohort,year,principal)] = dict(
            cohort=cohort, year=year, P=principal,
            indexed=int(indexed), inpatient_any=int(inpatient_any or 0),
            links_all=0,new_all=0,links_critical=0,new_critical=0,
            links_all_ed=0,new_all_ed=0,links_same=0,new_same=0,
            links_next=0,new_next=0,invalid_gap=0)
    if not rows:
        raise ValueError("No cohort rows")

    # Only linked patients need ED/IMP event lookups and flag checks.
    # Both evt and linked have primary-key indices on their join keys.
    linked_query = """
      WITH eligible AS (
        SELECT i.cohort,substr(i.start,1,4) AS yr,i.principal,
          CASE WHEN EXISTS(
            SELECT 1 FROM baseline.image im
            WHERE im.cohort=i.cohort AND im.patient=i.patient)
          THEN 1 ELSE 0 END AS any14,
          CASE WHEN UPPER(TRIM(COALESCE(ed.end_derived,'')))='F'
                 AND UPPER(TRIM(COALESCE(ip.start_derived,'')))='F'
          THEN 1 ELSE 0 END AS critical_f,
          CASE WHEN UPPER(TRIM(COALESCE(ed.derived,'')))='F'
                 AND UPPER(TRIM(COALESCE(ed.start_derived,'')))='F'
                 AND UPPER(TRIM(COALESCE(ed.end_derived,'')))='F'
                 AND UPPER(TRIM(COALESCE(ip.start_derived,'')))='F'
          THEN 1 ELSE 0 END AS all_ed_f,
          CAST(julianday(ip.start)-julianday(ed.end) AS INTEGER) AS lag
        FROM main.linked l
        JOIN main.idx i
          ON i.cohort=l.cohort AND i.patient=l.patient
        JOIN main.evt ed
          ON ed.patient=l.patient AND ed.encounter=l.ed
        JOIN main.evt ip
          ON ip.patient=l.patient AND ip.encounter=l.imp
      )
      SELECT cohort,yr,principal,
        COUNT(*) AS links_all,
        SUM(CASE WHEN any14=0 THEN 1 ELSE 0 END) AS new_all,
        SUM(critical_f) AS links_critical,
        SUM(CASE WHEN critical_f=1 AND any14=0 THEN 1 ELSE 0 END)
            AS new_critical,
        SUM(all_ed_f) AS links_all_ed,
        SUM(CASE WHEN all_ed_f=1 AND any14=0 THEN 1 ELSE 0 END)
            AS new_all_ed,
        SUM(CASE WHEN critical_f=1 AND lag=0 THEN 1 ELSE 0 END)
            AS links_same,
        SUM(CASE WHEN critical_f=1 AND lag=0 AND any14=0 THEN 1 ELSE 0 END)
            AS new_same,
        SUM(CASE WHEN critical_f=1 AND lag=1 THEN 1 ELSE 0 END)
            AS links_next,
        SUM(CASE WHEN critical_f=1 AND lag=1 AND any14=0 THEN 1 ELSE 0 END)
            AS new_next,
        SUM(CASE WHEN lag IS NULL OR lag NOT IN (0,1) THEN 1 ELSE 0 END)
            AS invalid_gap
      FROM eligible GROUP BY cohort,yr,principal
      ORDER BY cohort,yr,principal
    """
    measures = ("links_all","new_all","links_critical","new_critical",
                "links_all_ed","new_all_ed","links_same","new_same",
                "links_next","new_next","invalid_gap")
    for record in db.execute(linked_query):
        cohort, year, principal = record[:3]
        key = (cohort,year,principal)
        if key not in rows:
            raise ValueError("Linked ED refers to a nonexistent cohort/year/P")
        row = rows[key]
        row.update(zip(measures,(int(v or 0) for v in record[3:])))
        if row["invalid_gap"]:
            raise ValueError("Linked ED gap outside frozen 0-1 day window")
        if not (0 <= row["new_all_ed"] <= row["new_critical"] <= row["new_all"]
                <= row["links_all"] <= row["indexed"]):
            raise AssertionError("Ceiling monotonicity failed")
        if not (0 <= row["links_all_ed"] <= row["links_critical"]
                <= row["links_all"]):
            raise AssertionError("Date-provenance link counts not nested")
        if (row["links_same"] + row["links_next"] != row["links_critical"]
                or row["new_same"] + row["new_next"] != row["new_critical"]):
            raise AssertionError("Date gap partition failed")
        if row["inpatient_any"] + row["new_all"] > row["indexed"]:
            raise AssertionError("Upper bound exceeds indexed denominator")
    return list(rows.values())


def grouped(rows, by):
    if by not in ("cohort","P","year"):
        raise ValueError("Unsupported reporting stratum")
    groups={}
    for row in rows:
        key=(row["cohort"],) if by=="cohort" else (
            row["cohort"],row["P"] if by=="P" else row["year"])
        out=groups.setdefault(key,{k:0 for k in row if k not in ("cohort","year","P")})
        for k in out:
            out[k]+=row[k]
    return sorted(groups.items())


def show(rows):
    print("STEP66: provenance-sensitive HYPOTHETICAL ED-CPT14 ceiling")
    print("NO ED procedure scan. ED date link is NOT same-hospital verification.")
    print("P is unvalidated; T/F semantics from historical dictionary, not independently verified.")
    print("F strictness is a sensitivity rule, NOT evidence of correct dates.")
    print("Original Step62 indexed denominators and inpatient captures do not change.")
    for kind in ("cohort","P","year"):
        print("\nBY", kind.upper())
        for key,x in grouped(rows,kind):
            if x["indexed"] < 11:
                print(key, "suppressed: group n<11")
                continue
            n=x["indexed"]
            print(key,"n",n,"inpatient_any",x["inpatient_any"])
            for name, ln, added in (
                ("all unique ED", x["links_all"], x["new_all"]),
                ("ED end+IMP start both F", x["links_critical"], x["new_critical"]),
                ("all ED flags + IMP start F",x["links_all_ed"],x["new_all_ed"]),
                ("F critical dates, gap=0",x["links_same"],x["new_same"]),
                ("F critical dates, gap=1",x["links_next"],x["new_next"])):
                print(" ",name,"links",ln,"max_new",added,
                      "max_change_pp","%.2f"%(100*added/n))
    print("\nLOCAL ONLY. Institutional review required before external sharing.")
    print("Upper bounds are not actual new procedures, utilization, or treatment effects.")


def main():
    raw62=s62.PRIVATE / s62.DB.name
    raw63=s63.PRIVATE / s63.DATABASE
    if raw62.is_symlink() or raw63.is_symlink():
        raise ValueError("Symlinked source database not allowed")
    p62,p63=raw62.resolve(),raw63.resolve()
    if not p62.is_file() or not p63.is_file():
        raise FileNotFoundError("Completed Step62 and Step63 private databases required")
    with sqlite3.connect("file:"+str(p63)+"?mode=ro",uri=True) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:"+str(p62)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        print("Step66: verifying frozen read-only database snapshots...",
              flush=True)
        s64.verify(db,p62,p63)
        print("Step66: aggregating inpatient baseline and linked-ED subset...",
              flush=True)
        show(analyze(db))


if __name__=="__main__":
    main()
