#!/usr/bin/env python3
"""Step64: LOCAL-ONLY no-rescan ceiling on ED imaging-code augmentation.

Uses completed Step62/Step63 read-only SQLite. This estimates how much
recorded CPT14 code capture COULD rise if every uniquely linked ED
encounter contained a qualifying code; it does NOT claim those codes exist.
No IDs, source rows, or files are printed/written. Clinical approval and
disclosure review remain outside the script.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sqlite3

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63

MODALITIES = ("CT_HEAD", "MRI_BRAIN", "CTA_HEAD", "CTA_NECK",
              "MRA_HEAD", "MRA_NECK")
MEASURES = ("n", "linked", "baseline_any14", "max_new_any14") + tuple(
    part + "_" + modality
    for modality in MODALITIES
    for part in ("baseline", "max_new")
)


def analyze(db):
    """Aggregate each selected index patient once; never materialize IDs."""
    flags = ",\n".join(
        "MAX(CASE WHEN im.category='" + modality + "' THEN 1 ELSE 0 END) AS "
        + modality.lower()
        for modality in MODALITIES
    )
    counts = [
        "COUNT(*) AS n",
        "SUM(linked) AS linked",
        "SUM(any14) AS baseline_any14",
        "SUM(CASE WHEN linked=1 AND any14=0 THEN 1 ELSE 0 END) "
        "AS max_new_any14",
    ]
    for modality in MODALITIES:
        field = modality.lower()
        counts.extend((
            "SUM(" + field + ") AS baseline_" + modality,
            "SUM(CASE WHEN linked=1 AND " + field + "=0 THEN 1 ELSE 0 END) "
            "AS max_new_" + modality,
        ))
    sql = """
    WITH baseline AS (
      SELECT i.cohort, i.patient, substr(i.start,1,4) yr, i.principal,
             MAX(CASE WHEN im.category IS NOT NULL THEN 1 ELSE 0 END) any14,
             %s
      FROM baseline.idx i
      LEFT JOIN baseline.image im ON im.cohort=i.cohort AND im.patient=i.patient
      GROUP BY i.cohort,i.patient
    ),
    combined AS (
      SELECT b.*, CASE WHEN l.patient IS NULL THEN 0 ELSE 1 END linked
      FROM baseline b
      LEFT JOIN main.linked l ON l.cohort=b.cohort AND l.patient=b.patient
    )
    SELECT cohort,yr,principal,%s
    FROM combined
    GROUP BY cohort,yr,principal
    ORDER BY cohort,yr,principal
    """ % (flags, ",\n".join(counts))
    rows = []
    for record in db.execute(sql):
        cohort, year, p_label = record[:3]
        values = dict(zip(MEASURES, (int(v or 0) for v in record[3:])))
        for label in ("any14",) + MODALITIES:
            if values["baseline_" + label if label != "any14" else "baseline_any14"] + (
                values["max_new_" + label if label != "any14" else "max_new_any14"]
            ) > values["n"]:
                raise AssertionError("A theoretical outcome exceeded its denominator")
        if values["max_new_any14"] > values["linked"]:
            raise AssertionError("Increment exceeded the linked count")
        rows.append((cohort, year, int(p_label), values))
    if not rows:
        raise ValueError("No indexed patient aggregates")
    return rows


def summarize(rows, group):
    """Sum disjoint patient groups; the two overlapping cohorts stay separate."""
    groups = {}
    for cohort, yr, p_label, counts in rows:
        if group == "cohort":
            key = (cohort,)
        elif group == "P":
            key = (cohort, p_label)
        elif group == "year":
            key = (cohort, yr)
        else:
            raise ValueError("Unknown group")
        bucket = groups.setdefault(key, {name: 0 for name in MEASURES})
        for name in MEASURES:
            bucket[name] += counts[name]
    return sorted(groups.items())


def pct(n, denominator):
    return 100 * n / denominator if denominator else 0.


def show(rows):
    print("STEP64 READ-ONLY: hypothetical maximum ED code-capture improvement")
    print("No ED procedure rows have been scanned. These are UPPER BOUNDS, not estimates.")
    print("Linkage is date-only, not verified same-hospital or completed imaging.")
    print("Step62 cohort denominators are preserved, including ED-unassessable patients.")
    print()
    for (cohort,), x in summarize(rows, "cohort"):
        base = x["baseline_any14"]
        extra = x["max_new_any14"]
        assert base + extra <= x["n"]
        print("COHORT:", cohort)
        print("  indexed:", x["n"])
        print("  uniquely linked ED:", x["linked"],
              "(", "%.2f%%" % pct(x["linked"], x["n"]), "of indexed)")
        print("  existing inpatient ANY CPT14:", base,
              "(%.2f%%)" % pct(base, x["n"]))
        print("  maximum NEW patients possible from linked ED:", extra,
              "(%.2f percentage points)" % pct(extra, x["n"]))
        print("  absolute best-case ANY CPT14 total:",
              base + extra, "(%.2f%%)" % pct(base + extra, x["n"]))
        for modality in MODALITIES:
            b, e = x["baseline_" + modality], x["max_new_" + modality]
            print("  ", modality, "baseline", b, "maximum extra", e,
                  "absolute best-case rate %.2f%%" % pct(b + e, x["n"]))
        print()

    for label, title in (("P", "BY UNVALIDATED P LABEL"),
                         ("year", "BY INDEX YEAR")):
        print(title)
        for group, x in summarize(rows, label):
            # These outputs are for the authorized investigator locally,
            # not an externally release-approved disclosure table.
            if x["n"] < 11:
                print(group[0], "GROUP SUPPRESSED: n<11")
                continue
            print(group, "indexed", x["n"], "linked", x["linked"],
                  "inpatient_any14", x["baseline_any14"],
                  "max_new_any14", x["max_new_any14"],
                  "best_case_rate %.2f%%" %
                  pct(x["baseline_any14"] + x["max_new_any14"], x["n"]))
        print()
    print("Do not upload output without institutional disclosure review.")
    print("The upper bound is not a causal inference or imaging-completeness validation.")


def verify(db, step62_path, step63_path):
    if step62_path.is_symlink() or step63_path.is_symlink():
        raise ValueError("Private SQLite paths cannot be symlinks")
    stages = dict(db.execute("SELECT stage,done FROM baseline.progress"))
    if any(stages.get(stage) != 1 for stage in s62.STAGES):
        raise ValueError("Step62 must be completed through report")
    progress = dict(db.execute("SELECT stage,done FROM main.progress"))
    if progress.get("encounter") != 1 or progress.get("link") != 1:
        raise ValueError("Step63 encounter and link must both be complete")
    policy = db.execute("SELECT v FROM main.meta WHERE k='link_policy'").fetchone()
    if policy is None or policy[0] != s63.LINK_POLICY:
        raise ValueError("Step63 link policy does not match approved version")
    original = db.execute(
        "SELECT v FROM main.meta WHERE k='step62_snapshot'").fetchone()
    _, snapshot = s63._source_snapshot(step62_path.parent)
    if original is None or original[0] != snapshot:
        raise ValueError("Step62 changed since Step63 copied index memberships")
    different_idx = db.execute("""
      SELECT COUNT(*) FROM main.idx i
      LEFT JOIN baseline.idx b ON b.cohort=i.cohort AND b.patient=i.patient
      WHERE b.patient IS NULL OR b.encounter!=i.encounter OR b.start!=i.start
        OR b.end!=i.end OR b.principal!=i.principal""").fetchone()[0]
    if different_idx:
        raise ValueError("Step62 and Step63 index snapshots disagree")
    for cohort in s62.COHORTS:
        a = db.execute("SELECT COUNT(*) FROM main.idx WHERE cohort=?", (cohort,)
                       ).fetchone()[0]
        b = db.execute("SELECT COUNT(*) FROM baseline.idx WHERE cohort=?", (cohort,)
                       ).fetchone()[0]
        if a != b:
            raise ValueError("Step62 and Step63 index denominators disagree")
    orphans = db.execute("""
      SELECT COUNT(*) FROM main.linked l
      LEFT JOIN baseline.idx b
        ON b.cohort=l.cohort AND b.patient=l.patient AND b.encounter=l.imp
      WHERE b.patient IS NULL""").fetchone()[0]
    if orphans:
        raise ValueError("Orphaned Step63 linked membership")


def main():
    step62 = (s62.PRIVATE / s62.DB.name).resolve()
    step63 = (s63.PRIVATE / s63.DATABASE).resolve()
    if not step62.is_file() or not step63.is_file():
        raise FileNotFoundError("Both completed private SQLite databases are needed")
    with sqlite3.connect("file:" + str(step63) + "?mode=ro", uri=True) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:" + str(step62) + "?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        verify(db, step62, step63)
        show(analyze(db))


if __name__ == "__main__":
    main()
