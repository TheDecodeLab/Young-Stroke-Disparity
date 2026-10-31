#!/usr/bin/env python3
"""Step85: independent local-only support diagnostics for the P-standardized contrast.

Reuses frozen Step62/63/68 databases and Step69's indexed-patient aggregate.
Does not open the source ZIP or rescan source diagnosis/procedure tables.
Private detailed output is not suitable for publication.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
import json
import math
import os
from pathlib import Path
import sqlite3
import stat

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "results/phase1/full_reconstruction_private/step85_standardization_private"
OUTPUT = PRIVATE / "support_sensitivity_LOCAL_ONLY.json"
ACK = "I_CONFIRM_INTERNAL_REVIEW_ONLY"
THRESHOLDS = (11, 30, 50, 100)
METRICS = {
    "inpatient": ("inpatient",),
    "same_day": ("inpatient", "new_other_day0"),
}

def load_dependencies():
    try:
        from scripts import step62_checkpointed_cohort as s62
        from scripts import step63_ed_encounter_feasibility as s63
        from scripts import step64_ed_capture_ceiling as s64
        from scripts import step68_joint_imaging_window_scan as s68
        from scripts import step69_same_day_attachment_diagnostics as s69
        from scripts import step70_P_quarantine_standardization as s70
    except ModuleNotFoundError as e:
        if e.name != "scripts":
            raise
        import step62_checkpointed_cohort as s62
        import step63_ed_encounter_feasibility as s63
        import step64_ed_capture_ceiling as s64
        import step68_joint_imaging_window_scan as s68
        import step69_same_day_attachment_diagnostics as s69
        import step70_P_quarantine_standardization as s70
    return s62, s63, s64, s68, s69, s70

def _numerator(c, fields):
    return sum(int(c.get(k, 0)) for k in fields)

def _weighted(group, fields, min_n=1, exclude_year=None):
    """Restrict to supported common strata and restandardize their target mix.

    Every excluded stratum changes the target population. This is a sensitivity,
    not a replacement for the original full-cohort estimate.
    """
    original_n = 0
    retained_n = 0
    sums = [0.0, 0.0]
    retained = []
    for key, pmap in sorted(group.items()):
        if set(pmap) != {0, 1}:
            raise ValueError("Missing P group in standardization stratum")
        a, b = pmap[0], pmap[1]
        n0, n1 = int(a["n"]), int(b["n"])
        if n0 <= 0 or n1 <= 0:
            raise ValueError("Zero P-group support in original standardization")
        n = n0+n1
        original_n += n
        if exclude_year is not None and key[0] == exclude_year:
            continue
        if min(n0,n1) < min_n:
            continue
        for p, num in enumerate((_numerator(a, fields), _numerator(b, fields))):
            den = (n0, n1)[p]
            if num < 0 or num > den:
                raise ValueError("Non-binomial endpoint")
            sums[p] += n*num/den
        retained_n += n
        retained.append(key)
    if not retained_n:
        return {"available": False, "original_n": original_n, "retained_n": 0}
    probs = [100*v/retained_n for v in sums]
    return {
        "available": True,
        "original_n": original_n,
        "retained_n": retained_n,
        "coverage": retained_n/original_n,
        "P0_pct": probs[0], "P1_pct": probs[1],
        "P1_minus_P0_pp": probs[1]-probs[0],
        "retained_strata": len(retained),
    }

def summarize(counts, cohort, s70):
    group = s70.strata(counts, cohort, "year_and_quarantine")
    if not group or any(len(key) != 2 for key in group):
        raise ValueError("Expected year x ambiguity strata")
    n_total = sum(sum(int(c["n"]) for c in cells.values()) for cells in group.values())
    if n_total != int(counts[("COHORT", cohort)]["n"]):
        raise ValueError("Year x ambiguity denominator mismatch")
    if n_total <= 0:
        raise ValueError("Empty primary cohort")
    details = []
    for key, cells in sorted(group.items()):
        if set(cells) != {0,1}:
            raise ValueError("Incomplete source-P overlap")
        n0, n1 = (int(cells[p]["n"]) for p in (0,1))
        if min(n0,n1) == 0:
            raise ValueError("Original standardization has empty P stratum")
        details.append({"year":key[0], "ambiguity":key[1], "P0_n":n0,
                        "P1_n":n1, "min_P_n":min(n0,n1)})
    result = {
        "policy": "STEP85_PRIVATE_AGGREGATE_SUPPORT_NOT_FOR_PUBLIC_RELEASE",
        "cohort": cohort, "n_indexed": n_total,
        "strata": details,
        "thresholds": {},
        "metrics": {},
        "interpretation": (
            "Sparse-cell exclusion, era pooling, and leave-one-year-out checks "
            "change the descriptive standardization target. They do not provide "
            "hospital clustering or a clinically causal interpretation."
        ),
    }
    years = sorted(set(k[0] for k in group))
    if years != [str(v) for v in range(2016, 2025)]:
        raise ValueError("Unexpected calendar-year coverage")
    for threshold in THRESHOLDS:
        result["thresholds"][str(threshold)] = {
            "all_strata_adequate": all(d["min_P_n"] >= threshold for d in details),
            "strata_below_threshold": sum(d["min_P_n"] < threshold for d in details),
        }
    # In particular verify the reported -3.66% point same-day result.
    for label, fields in METRICS.items():
        full = _weighted(group, fields)
        independent = s70.standardized(counts, cohort, fields, "year_and_quarantine")
        if not math.isclose(full["P1_minus_P0_pp"], independent[2], abs_tol=1e-9):
            raise ValueError("Independent standardized estimate mismatch")
        thresholds = {str(t):_weighted(group, fields, t) for t in THRESHOLDS}
        loo = {year:_weighted(group, fields, exclude_year=year) for year in years}
        # Three-year eras cannot reproduce year-level standardization and are only sensitivity.
        era_groups = {}
        for (year, held), pmap in group.items():
            year_i = int(year)
            era = "2016-2018" if year_i<=2018 else "2019-2021" if year_i<=2021 else "2022-2024"
            dest = era_groups.setdefault((era,held),{0:Counter(),1:Counter()})
            for p in (0,1):
                dest[p].update(pmap[p])
        era = _weighted(era_groups, fields)
        result["metrics"][label] = {
            "full": full,
            "thresholded": thresholds,
            "leave_one_year_out": loo,
            "pooled_three_year_era": era,
            "all_loo_same_sign": all(
                x["available"] and x["P1_minus_P0_pp"]*full["P1_minus_P0_pp"] > 0
                for x in loo.values()
            ),
        }
    return result

def save_private(path, report):
    path = path.expanduser()
    permitted = ROOT / "results/phase1/full_reconstruction_private"
    target = path.resolve()
    if permitted.resolve() not in target.parents:
        raise ValueError("Output must remain inside gitignored full_reconstruction_private")
    if path.is_symlink():
        raise ValueError("Refusing symlink output")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--acknowledge", required=True)
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args=ap.parse_args()
    if args.acknowledge != ACK:
        ap.error("Explicit restricted-internal-review acknowledgement required")
    s62,s63,s64,s68,s69,s70=load_dependencies()
    paths=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise FileNotFoundError("One or more frozen local checkpoints missing")
    report_path=s68.PRIVATE/s68.REPORT
    if report_path.is_symlink() or not report_path.is_file():
        raise FileNotFoundError("Frozen Step68 reference unavailable")
    frozen=json.loads(report_path.read_text(encoding="utf8"))
    if frozen.get("stage") != s68.POLICY:
        raise ValueError("Step68 source-policy mismatch")
    db62,db63,db68 = (p.resolve() for p in paths)
    with closing(sqlite3.connect("file:"+str(db63)+"?mode=ro",uri=True)) as db:
        db.execute("ATTACH DATABASE ? AS baseline",("file:"+str(db62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",("file:"+str(db68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,db62,db63)
        frozen_meta=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if frozen_meta is None:
            raise ValueError("Step68 frozen marker absent")
        m=json.loads(frozen_meta[0])
        if m.get("policy") != s68.POLICY or m.get("s62") != s68._snapshot(db62) or m.get("s63") != s68._snapshot(db63):
            raise ValueError("Checkpoint source signature mismatch")
        counts=s69.aggregate(db)
        s69.verify_aggregate(db,counts,frozen)
        report=summarize(counts,s62.COHORTS[0],s70)
    save_private(args.output,report)
    # Only statuses; never print stratum counts or sensitive effect estimates.
    print("STEP85 LOCAL ONLY: frozen standardization sensitivity completed")
    for threshold in THRESHOLDS:
        print("All year x ambiguity x P denominators >=",threshold,":",
              "YES" if report["thresholds"][str(threshold)]["all_strata_adequate"] else "NO")
    x=report["metrics"]["same_day"]
    print("Full-data sign robust to 3-year era pooling:",
          "YES" if x["pooled_three_year_era"]["P1_minus_P0_pp"]*x["full"]["P1_minus_P0_pp"]>0 else "NO")
    print("Full-data sign consistent across leave-one-year-out:", "YES" if x["all_loo_same_sign"] else "NO")
    for threshold in THRESHOLDS:
        q=x["thresholded"][str(threshold)]
        print("Threshold",threshold,"coverage >=95%:",
              "YES" if q["available"] and q["coverage"]>=0.95 else "NO",
              "same sign:",
              "YES" if q["available"] and q["P1_minus_P0_pp"]*x["full"]["P1_minus_P0_pp"]>0 else "NO_OR_UNAVAILABLE")
    print("Detailed restricted result:",args.output)
    print("No full source scan. Do not upload private report or publish exploratory effects from this QA.")

if __name__ == "__main__":
    main()
