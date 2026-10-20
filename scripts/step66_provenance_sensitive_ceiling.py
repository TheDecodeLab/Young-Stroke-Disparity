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
    """Aggregate-only rows. No identifier or individual encounter returned."""
    query = """
    WITH baseline AS (
      SELECT i.cohort,i.patient,i.encounter,i.principal,
             substr(i.start,1,4) AS yr,
             MAX(CASE WHEN im.category IS NOT NULL THEN 1 ELSE 0 END) AS any14
      FROM baseline.idx i
      LEFT JOIN baseline.image im
        ON im.cohort=i.cohort AND im.patient=i.patient
      GROUP BY i.cohort,i.patient
    ),
    eligible AS (
      SELECT b.cohort,b.patient,b.yr,b.principal,b.any14,
             CASE WHEN l.patient IS NOT NULL THEN 1 ELSE 0 END AS linked,
             CASE WHEN l.patient IS NOT NULL
                   AND UPPER(TRIM(COALESCE(ed.end_derived,'')))='F'
                   AND UPPER(TRIM(COALESCE(ip.start_derived,'')))='F'
                  THEN 1 ELSE 0 END AS critical_f,
             CASE WHEN l.patient IS NOT NULL
                   AND UPPER(TRIM(COALESCE(ed.derived,'')))='F'
                   AND UPPER(TRIM(COALESCE(ed.start_derived,'')))='F'
                   AND UPPER(TRIM(COALESCE(ed.end_derived,'')))='F'
                   AND UPPER(TRIM(COALESCE(ip.start_derived,'')))='F'
                  THEN 1 ELSE 0 END AS all_ed_f,
             CASE WHEN l.patient IS NOT NULL
                   THEN CAST(julianday(
                     substr(i.start,1,4)||'-'||substr(i.start,5,2)||'-'||substr(i.start,7,2)
                   ) - julianday(ed.end) AS INTEGER)
                  ELSE NULL END AS lag
      FROM baseline b
      JOIN main.idx i ON i.cohort=b.cohort AND i.patient=b.patient
      LEFT JOIN main.linked l ON l.cohort=b.cohort AND l.patient=b.patient
      LEFT JOIN main.evt ed ON ed.patient=l.patient AND ed.encounter=l.ed
      LEFT JOIN main.evt ip ON ip.patient=i.patient AND ip.encounter=i.encounter
    )
    SELECT cohort,yr,principal,
           COUNT(*) AS indexed,
           SUM(any14) AS inpatient_any,
           SUM(linked) AS linked_total,
           SUM(CASE WHEN linked=1 AND any14=0 THEN 1 ELSE 0 END) AS new_all,
           SUM(critical_f) AS links_critical_f,
           SUM(CASE WHEN critical_f=1 AND any14=0 THEN 1 ELSE 0 END)
                AS new_critical_f,
           SUM(all_ed_f) AS links_all_ed_f,
           SUM(CASE WHEN all_ed_f=1 AND any14=0 THEN 1 ELSE 0 END)
                AS new_all_ed_f,
           SUM(CASE WHEN critical_f=1 AND lag=0 THEN 1 ELSE 0 END)
                AS links_same,
           SUM(CASE WHEN critical_f=1 AND lag=0 AND any14=0 THEN 1 ELSE 0 END)
                AS new_same,
           SUM(CASE WHEN critical_f=1 AND lag=1 THEN 1 ELSE 0 END)
                AS links_next,
           SUM(CASE WHEN critical_f=1 AND lag=1 AND any14=0 THEN 1 ELSE 0 END)
                AS new_next,
           SUM(CASE WHEN linked=1 AND (lag IS NULL OR lag NOT IN (0,1))
                    THEN 1 ELSE 0 END) AS invalid_gap
    FROM eligible
    GROUP BY cohort,yr,principal
    ORDER BY cohort,yr,principal
    """
    # A linked ED must have a retained event, because Step63's linked
    # candidates were derived from the retained evt table. Validate
    # from event join in a separate count before executing the aggregate.
    missing = db.execute("""
        SELECT COUNT(*) FROM main.linked l
        LEFT JOIN main.evt e
          ON e.patient=l.patient AND e.encounter=l.ed
        WHERE e.patient IS NULL""").fetchone()[0]
    if missing:
        raise ValueError("Step63 linked ED event missing")
    cols = ("cohort","year","P","indexed","inpatient_any","links_all","new_all",
            "links_critical","new_critical","links_all_ed","new_all_ed",
            "links_same","new_same","links_next","new_next","invalid_gap")
    result=[]
    for rec in db.execute(query):
        row=dict(zip(cols,rec))
        for name in cols[3:]:
            row[name] = int(row[name] or 0)
        if row["invalid_gap"] != 0:
            raise ValueError("Linked ED gap outside frozen 0-1 day window")
        if not (0 <= row["new_all_ed"] <= row["new_critical"] <= row["new_all"]
                <= row["links_all"] <= row["indexed"]):
            raise AssertionError("Ceiling monotonicity failed")
        if (row["links_same"] + row["links_next"] != row["links_critical"]
                or row["new_same"] + row["new_next"] != row["new_critical"]):
            raise AssertionError("Date gap partition failed")
        if row["inpatient_any"] + row["new_all"] > row["indexed"]:
            raise AssertionError("Upper bound exceeds indexed denominator")
        result.append(row)
    if not result:
        raise ValueError("No cohort rows")
    return result


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
        s64.verify(db,p62,p63)
        show(analyze(db))


if __name__=="__main__":
    main()
