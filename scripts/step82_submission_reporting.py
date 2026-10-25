#!/usr/bin/env python3
"""Step82: LOCAL ONLY cohort flow and baseline characteristics.

Use the frozen Step62 SQLite database without reading the TriNetX ZIP. This
produces an INTERNAL report, not an approved public aggregate release.
The flow begins with qualifying, date-valid I63/IMP admission keys retained
by Step62. It does not claim to represent all source I63 diagnoses.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT / "results/phase1/full_reconstruction_private"
DB = PRIVATE_ROOT / "step62_cohort_private/provisional_cohort_LOCAL_ONLY.sqlite"
OUTPUT_DIR = PRIVATE_ROOT / "step82_submission_reporting_private"
OUTPUT = "cohort_flow_baseline_INTERNAL_ONLY.json"
PRIMARY = "uniform_18_50"
REQUIRED_STAGES = ("diagnosis", "encounter", "patient", "index", "procedure", "report")
MIN_CELL = 11
AGE_BANDS = ((18, 24), (25, 34), (35, 44), (45, 50))
# Names are stable source-derived coding categories, never raw source labels.
ALLOWED = {
    "SEX": {"MALE", "FEMALE", "UNKNOWN_MISSING", "OTHER_OR_UNMAPPED"},
    "RACE": {"WHITE", "BLACK_AFRICAN_AMERICAN", "ASIAN", "AIAN", "NHPI",
             "MULTIRACIAL", "UNKNOWN_MISSING", "OTHER_OR_UNMAPPED"},
    "ETHNICITY": {"HISPANIC_LATINO", "NOT_HISPANIC_LATINO", "UNKNOWN_MISSING",
                  "OTHER_OR_UNMAPPED"},
}


def check_frozen(db):
    """Reject partial source scans, wrong structures and conflicting counts."""
    statuses = dict(db.execute("SELECT stage, done FROM progress"))
    if any(statuses.get(stage) != 1 for stage in REQUIRED_STAGES):
        raise ValueError("The Step62 frozen stages are not all complete")
    required_tables = {"admission", "ambiguous_admission", "person", "idx", "audit"}
    available = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if not required_tables.issubset(available):
        raise ValueError("Step62 checkpoint schema mismatch")
    expected = db.execute("SELECT COUNT(*) FROM idx WHERE cohort=?", (PRIMARY,)).fetchone()[0]
    if expected <= 0:
        raise ValueError("No primary index patients")
    return expected


def classify_patient(statuses, indexed):
    """Mutually exclusive patient-level routing, not admission-level exclusions."""
    s = set(statuses)
    if indexed:
        if "definite" not in s:
            raise AssertionError("Indexed patient has no definitely eligible admission")
        return "included_indexed"
    if "definite" in s:
        return "held_competing_same_day_definite_index"
    for flag, result in (
        ("unknown_yob", "no_definite_missing_birth_year"),
        ("unknown_sex", "no_definite_unknown_sex"),
        ("boundary_uncertain", "no_definite_age_boundary_uncertain"),
        ("excluded", "no_definite_age_outside_range"),
    ):
        if flag in s:
            return result
    raise ValueError("Candidate patient has no recognized age-status flag")


def cohort_flow(db, cohort, age_class):
    """Read one candidate admission at a time, classify each distinct patient."""
    indexed = db.execute("SELECT COUNT(*) FROM idx WHERE cohort=?", (cohort,)).fetchone()[0]
    sql = """
      SELECT a.patient, a.start, p.yob, p.sex,
             CASE WHEN i.patient IS NULL THEN 0 ELSE 1 END AS is_indexed
      FROM admission a
      LEFT JOIN person p ON p.patient=a.patient
      LEFT JOIN idx i ON i.patient=a.patient AND i.cohort=?
      ORDER BY a.patient, a.start, a.encounter
    """
    patients = Counter()
    admissions = Counter()
    current = None
    group_statuses = []
    group_indexed = False

    def finish():
        if current is not None:
            patients[classify_patient(group_statuses, group_indexed)] += 1

    for patient, start, yob, sex, is_indexed in db.execute(sql, (cohort,)):
        if patient != current:
            finish()
            current = patient
            group_statuses = []
            group_indexed = bool(is_indexed)
        elif group_indexed != bool(is_indexed):
            raise AssertionError("Patient index flag varies across admissions")
        status = age_class(start, yob, sex, cohort)
        group_statuses.append(status)
        admissions["candidate_admission_age_" + status] += 1
    finish()

    if patients["included_indexed"] != indexed:
        raise AssertionError("Patient flow does not reconcile to frozen idx")
    expected_audit = dict(db.execute(
        "SELECT finding,n FROM audit WHERE cohort=?", (cohort,)))
    for name, actual in admissions.items():
        if int(expected_audit.get(name, -1)) != actual:
            raise AssertionError("Admission-level age audit differs: " + name)
    for name, n in expected_audit.items():
        if name.startswith("candidate_admission_age_") and admissions.get(name, 0) != n:
            raise AssertionError("Age-audit category missing: " + name)
    tie_name = "patient_held_competing_same_day_index_encounters"
    if patients["held_competing_same_day_definite_index"] != expected_audit.get(tie_name, 0):
        raise AssertionError("Competing same-day patient count differs from Step62")
    n_keys = db.execute("SELECT COUNT(*) FROM admission").fetchone()[0]
    if sum(admissions.values()) != n_keys:
        raise AssertionError("Admission row count does not reconcile")
    unique = sum(patients.values())
    if unique < indexed or n_keys < unique:
        raise AssertionError("Invalid patient/key denominators")
    return {
        "source_scope": "retained date-valid same-patient/encounter I63-coded IMP keys",
        "candidate_retained_imp_keys": n_keys,
        "candidate_unique_patients": unique,
        "patient_flow": dict(sorted(patients.items())),
        "patient_partition_reconciles": unique == sum(patients.values()),
        "indexed_patients_reconcile": indexed,
        "admission_age_audit_not_patient_exclusions": dict(sorted(admissions.items())),
    }


def age_band(start, yob):
    """Only assign a band when all birth-year-compatible ages fit it."""
    if not isinstance(yob, int) or len(start) < 4:
        return "UNKNOWN_BIRTH_YEAR"
    maximum = int(start[:4]) - yob
    minimum = maximum - 1
    for a, b in AGE_BANDS:
        if a <= minimum and maximum <= b:
            return f"{a}-{b}"
    return "CROSSES_AGE_BAND_BOUNDARY"


def _cat(kind, value, category):
    label = category(kind, value)
    if label not in ALLOWED[kind]:
        raise ValueError("Unexpected mapped category from Step71: " + kind)
    return label


def baseline(db, cohort, category):
    """Counts by mutually exclusive dimensions; overall, P=0, P=1."""
    dims = ("SEX", "RACE", "ETHNICITY", "AGE_BAND", "INDEX_YEAR")
    counts = {name: defaultdict(Counter) for name in dims}
    n = 0
    grouped_P = Counter()
    sql = """
       SELECT i.start, i.principal, p.yob, p.sex, p.race, p.ethnicity
       FROM idx i LEFT JOIN person p ON p.patient=i.patient
       WHERE i.cohort=? ORDER BY i.patient
    """
    for start, principal, yob, sex, race, ethnicity in db.execute(sql, (cohort,)):
        if principal not in (0, 1):
            raise ValueError("Unrecognized principal-I63 source flag")
        n += 1
        grouped_P[principal] += 1
        values = {
            "SEX": _cat("SEX", sex, category),
            "RACE": _cat("RACE", race, category),
            "ETHNICITY": _cat("ETHNICITY", ethnicity, category),
            "AGE_BAND": age_band(start, yob),
            "INDEX_YEAR": start[:4],
        }
        for name, value in values.items():
            counts[name][value]["overall"] += 1
            counts[name][value]["P" + str(principal)] += 1
    expected = db.execute("SELECT COUNT(*),SUM(principal) FROM idx WHERE cohort=?", (cohort,)).fetchone()
    if expected != (n, grouped_P[1]):
        raise AssertionError("Frozen cohort / P numerator mismatch")
    summary = {}
    disclosures = []
    for dim, categories in counts.items():
        table = []
        for label, c in sorted(categories.items()):
            row = {
                "category": label,
                "n_total": c["overall"], "pct_total": round(100*c["overall"]/n, 2),
                "n_P0": c["P0"], "pct_P0": round(100*c["P0"]/grouped_P[0], 2),
                "n_P1": c["P1"], "pct_P1": round(100*c["P1"]/grouped_P[1], 2),
            }
            for num, denom, label_suffix in (
                (c["overall"], n, "total"),
                (c["P0"], grouped_P[0], "P0"),
                (c["P1"], grouped_P[1], "P1"),
            ):
                if 0 < num < MIN_CELL or 0 < denom-num < MIN_CELL:
                    disclosures.append(f"{dim}:{label}:{label_suffix}")
            table.append(row)
        for field, expected_n in (("n_total", n), ("n_P0", grouped_P[0]), ("n_P1", grouped_P[1])):
            if sum(r[field] for r in table) != expected_n:
                raise AssertionError("Baseline category partition mismatch: " + dim)
        summary[dim] = table
    return {
        "n": n,
        "P0": grouped_P[0],
        "P1": grouped_P[1],
        "category_tables": summary,
        "preliminary_small_cell_or_complement_flags": disclosures,
    }


def aggregate_report(db, age_class, category):
    expected_n = check_frozen(db)
    flow = cohort_flow(db, PRIMARY, age_class)
    chars = baseline(db, PRIMARY, category)
    if flow["indexed_patients_reconcile"] != chars["n"] or expected_n != chars["n"]:
        raise AssertionError("Selection and baseline denominators disagree")
    quarantine = db.execute("SELECT COUNT(*) FROM ambiguous_admission").fetchone()[0]
    return {
        "policy": "STEP82_INTERNAL_ONLY_NOT_RELEASE_APPROVED",
        "study": "TriNetX Research Network I63-coded IMP, definite age 18-50, 2016-2024",
        "notice": "No raw identifiers. Counts still require institutional aggregate and cumulative-disclosure review.",
        "patient_flow_not_full_export_flow": flow,
        "quarantined_conflicting_imp_keys_outside_flow": quarantine,
        "baseline": chars,
        "limitations": [
            "The flow starts after diagnosis/encounter matching. It cannot count all source I63 candidates or unassessable source rows.",
            "Admission-level age-status counts are not person-level exclusions.",
            "Conflicting encounter keys are reported separately and may involve patients with other retained keys.",
            "Age-band labels are certain only if both possible ages from birth year fall within the band.",
            "Source demographic categories are conservatively mapped, not clinically validated.",
            "No performed-imaging, hospital-level clustering, or clinical stroke adjudication is implied.",
        ],
    }


def verify_frozen_step62_report(result, source_report):
    """Cross-check a second frozen Step62 artifact, not only internal SQLite."""
    if source_report.get("stage") != "STEP62_PROVISIONAL_PRIVATE_RECONSTRUCTION":
        raise ValueError("Unexpected Step62 frozen aggregate report policy")
    original = source_report.get("cohorts", {}).get(PRIMARY, {})
    expected_n = original.get("indexed_patients_not_validated")
    if expected_n != result["baseline"]["n"]:
        raise AssertionError("Step62 report index denominator mismatch")
    years = original.get("by_start_year", {})
    if sum(int(v["index_cases"]) for v in years.values()) != expected_n:
        raise AssertionError("Step62 year partitions differ from index total")
    if sum(int(v["with_P_label"]) for v in years.values()) != result["baseline"]["P1"]:
        raise AssertionError("Step62 P flag count differs from baseline")
    source_audit = original.get("candidate_admission_age_QA_NOT_patient_denominators")
    if not isinstance(source_audit, dict):
        raise ValueError("Step62 frozen age-audit missing")
    for key, n in result["patient_flow_not_full_export_flow"]["admission_age_audit_not_patient_exclusions"].items():
        if source_audit.get(key) != n:
            raise AssertionError("Step62 frozen age-audit mismatch: " + key)
    held = result["patient_flow_not_full_export_flow"]["patient_flow"].get(
        "held_competing_same_day_definite_index", 0)
    if source_audit.get("patient_held_competing_same_day_index_encounters", 0) != held:
        raise AssertionError("Step62 frozen held-index count mismatch")
    source_integrity = source_report.get("encounter_key_integrity_LOCAL_ONLY", {})
    if source_integrity.get("quarantined_qualifying_IMP_keys_with_conflicting_dates") != result["quarantined_conflicting_imp_keys_outside_flow"]:
        raise AssertionError("Step62 frozen quarantined-key count mismatch")
    source_keys = source_integrity.get("remaining_matched_IMP_encounter_keys")
    if source_keys != result["patient_flow_not_full_export_flow"]["candidate_retained_imp_keys"]:
        raise AssertionError("Step62 frozen retained encounter-key count mismatch")
    return True


def write_private_report(report, out_folder):
    base = PRIVATE_ROOT.resolve()
    folder = Path(out_folder).expanduser().resolve()
    if base not in folder.parents:
        raise ValueError("Output must stay under gitignored full_reconstruction_private")
    if Path(out_folder).is_symlink():
        raise ValueError("Private output directory must not be symlink")
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    dest = folder / OUTPUT
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("Private aggregate report exists, no overwrite")
    fd = os.open(str(dest), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
            f.write("\n")
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return dest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--acknowledge", required=True, choices=["I_CONFIRM_INTERNAL_REVIEW_ONLY"])
    args = parser.parse_args(argv)
    if args.db.is_symlink() or not args.db.is_file():
        raise FileNotFoundError("Frozen Step62 database not found or is a symlink")
    if PRIVATE_ROOT.resolve() not in args.db.resolve().parents:
        raise ValueError("Step62 database must be inside local private results")
    prior_path=args.db.parent / "aggregate_review_LOCAL_ONLY.json"
    if prior_path.is_symlink() or not prior_path.is_file():
        raise FileNotFoundError("Step62 frozen aggregate report missing")
    prior=json.loads(prior_path.read_text(encoding="utf-8"))
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step71_demographic_capture_feasibility as s71
    if PRIMARY != s62.COHORTS[0]:
        raise ValueError("Primary cohort policy has changed")
    with sqlite3.connect("file:"+str(args.db.resolve())+"?mode=ro",uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        report=aggregate_report(db, s62.age_class, s71.category)
        verify_frozen_step62_report(report, prior)
    dest=write_private_report(report,args.output_dir)
    print("STEP82 LOCAL ONLY: baseline and patient-level flow completed")
    print("Report:", dest)
    print("Indexed patients:", report["baseline"]["n"])
    print("Source cohort P=0 / P=1:",report["baseline"]["P0"],report["baseline"]["P1"])
    print("Selection partition: PASS; demographic partitions: PASS")
    print("Small-cell/complement flagged cells:",
          len(report["baseline"]["preliminary_small_cell_or_complement_flags"]))
    print("Do not upload private file or publish counts before disclosure approval.")


if __name__ == "__main__":
    main()
