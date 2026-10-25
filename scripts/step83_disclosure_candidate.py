#!/usr/bin/env python3
"""Step83: internal-only publication-table candidate from frozen Step82 JSON.

Never reads source data or IDs. All generated cells remain restricted until
institutional review, including cumulative disclosure across all manuscript
exhibits. We avoid reconstructible P-specific sex cells by showing only the
overall sex distribution, not by hiding a single P-specific cell.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT / "results/phase1/full_reconstruction_private"
STEP82 = (PRIVATE_ROOT / "step82_submission_reporting_private" /
          "cohort_flow_baseline_INTERNAL_ONLY.json")
OUTPUT_DIR = PRIVATE_ROOT / "step83_reporting_candidate_private"
DIMS = ("SEX", "RACE", "ETHNICITY", "AGE_BAND", "INDEX_YEAR")
MIN_CELL = 11
VALID_CATEGORIES = {
    "SEX": {"MALE", "FEMALE", "UNKNOWN_MISSING", "OTHER_OR_UNMAPPED"},
    "RACE": {"WHITE", "BLACK_AFRICAN_AMERICAN", "ASIAN", "AIAN", "NHPI",
             "MULTIRACIAL", "UNKNOWN_MISSING", "OTHER_OR_UNMAPPED"},
    "ETHNICITY": {"HISPANIC_LATINO", "NOT_HISPANIC_LATINO",
                  "UNKNOWN_MISSING", "OTHER_OR_UNMAPPED"},
    "AGE_BAND": {"18-24", "25-34", "35-44", "45-50",
                 "CROSSES_AGE_BAND_BOUNDARY", "UNKNOWN_BIRTH_YEAR"},
    "INDEX_YEAR": {str(y) for y in range(2016, 2025)},
}
ACK = "I_CONFIRM_INTERNAL_REVIEW_ONLY"


def _positive_int(n, name, allow_zero=True):
    if isinstance(n, bool) or not isinstance(n, int) or n < (0 if allow_zero else 1):
        raise ValueError("Invalid nonnegative count: " + name)
    return n


def flagged(n, denominator):
    """Match Step82's preliminary policy; zero itself is not flagged."""
    _positive_int(n, "cell")
    _positive_int(denominator, "denominator", allow_zero=False)
    if n > denominator:
        raise ValueError("Cell exceeds its denominator")
    return (0 < n < MIN_CELL or 0 < denominator - n < MIN_CELL)


def pct(n, denominator):
    return round(100.0 * n / denominator, 2)


def validate_source(source):
    if source.get("policy") != "STEP82_INTERNAL_ONLY_NOT_RELEASE_APPROVED":
        raise ValueError("Unexpected Step82 private report policy")
    base = source["baseline"]
    n = _positive_int(base["n"], "baseline n", allow_zero=False)
    n0 = _positive_int(base["P0"], "baseline P0", allow_zero=False)
    n1 = _positive_int(base["P1"], "baseline P1", allow_zero=False)
    if n0 + n1 != n:
        raise AssertionError("P partition does not reconcile")
    tables = base["category_tables"]
    if set(tables) != set(DIMS):
        raise ValueError("Missing or unexpected baseline dimension")
    regenerated = set()
    for dim in DIMS:
        rows = tables[dim]
        if not isinstance(rows, list) or not rows:
            raise ValueError("Empty baseline dimension: " + dim)
        names = set()
        totals = {"n_total": 0, "n_P0": 0, "n_P1": 0}
        for row in rows:
            category = row["category"]
            if (not isinstance(category, str) or not category or
                    category in names or category not in VALID_CATEGORIES[dim]):
                raise ValueError("Invalid or duplicate category label in " + dim)
            names.add(category)
            for key, den, suffix, percent in (
                ("n_total", n, "total", "pct_total"),
                ("n_P0", n0, "P0", "pct_P0"),
                ("n_P1", n1, "P1", "pct_P1"),
            ):
                cell = _positive_int(row[key], dim + " " + key)
                totals[key] += cell
                if flagged(cell, den):
                    regenerated.add(dim + ":" + category + ":" + suffix)
                if abs(float(row[percent]) - pct(cell, den)) > 0.005:
                    raise AssertionError("Source percentage mismatch in " + dim)
            if row["n_total"] != row["n_P0"] + row["n_P1"]:
                raise AssertionError("P-specific category numerator mismatch in " + dim)
        if totals != {"n_total": n, "n_P0": n0, "n_P1": n1}:
            raise AssertionError("Baseline dimension denominator mismatch: " + dim)
    declared = base["preliminary_small_cell_or_complement_flags"]
    if not isinstance(declared, list) or any(not isinstance(x, str) for x in declared):
        raise ValueError("Malformed Step82 flags")
    if len(declared) != len(set(declared)) or regenerated != set(declared):
        raise AssertionError("Step82 disclosure flags disagree with independent screen")

    flow = source["patient_flow_not_full_export_flow"]
    if flow["source_scope"] != "retained date-valid same-patient/encounter I63-coded IMP keys":
        raise ValueError("Unsupported candidate-flow source scope")
    unique = _positive_int(flow["candidate_unique_patients"], "candidate people", False)
    keys = _positive_int(flow["candidate_retained_imp_keys"], "candidate keys", False)
    if keys < unique:
        raise AssertionError("Fewer qualifying keys than candidate people")
    partition = flow["patient_flow"]
    if not isinstance(partition, dict) or not partition:
        raise ValueError("Missing patient flow")
    if sum(_positive_int(x, "patient-flow group") for x in partition.values()) != unique:
        raise AssertionError("Patient-level selection does not partition candidate people")
    if partition.get("included_indexed") != n or flow["indexed_patients_reconcile"] != n:
        raise AssertionError("Baseline and selection denominator disagree")
    if flow["patient_partition_reconciles"] is not True:
        raise AssertionError("Step82 selection partition not verified")
    allowed = {"included_indexed", "held_competing_same_day_definite_index",
               "no_definite_missing_birth_year", "no_definite_unknown_sex",
               "no_definite_age_boundary_uncertain", "no_definite_age_outside_range"}
    if not set(partition).issubset(allowed):
        raise ValueError("Unexpected selection-flow status")
    return n, n0, n1, unique, regenerated


def prepare(source):
    n, n0, n1, unique, source_flags = validate_source(source)
    nonindexed = unique - n
    if flagged(n, unique) or flagged(nonindexed, unique):
        raise ValueError("Candidate flow would reveal a small retained/excluded group")
    raw_flow = source["patient_flow_not_full_export_flow"]["patient_flow"]
    held = raw_flow.get("held_competing_same_day_definite_index", 0)
    no_definite = nonindexed - held
    if no_definite < 0:
        raise AssertionError("Invalid patient-flow partition")
    flows = [{"reason": "Included indexed patients", "n": n}]
    if held and no_definite and not flagged(held, unique) and not flagged(no_definite, unique):
        flows += [
            {"reason": "Held: competing same-day index candidates", "n": held},
            {"reason": "No definitely age-eligible candidate admission", "n": no_definite},
        ]
        flow_policy = "three_groups"
    else:
        flows.append({"reason": "Not indexed for eligibility or tie reasons", "n": nonindexed})
        flow_policy = "collapsed_exclusions"
    if sum(x["n"] for x in flows) != unique:
        raise AssertionError("Released flow partition does not reconcile")

    out_dims = {}
    policies = {}
    for dim in DIMS:
        src = source["baseline"]["category_tables"][dim]
        overall_risk = any(flagged(r["n_total"], n) for r in src)
        strat_risk = any(flagged(r["n_P0"], n0) or flagged(r["n_P1"], n1)
                         for r in src)
        if overall_risk:
            # Do not show even one row from a partly undisclosable dimension.
            policies[dim] = "withheld_entire_dimension"
            continue
        # Always withhold the sex-by-P breakdown, even if no cell is small.
        show_P = dim != "SEX" and not strat_risk
        policies[dim] = "P_stratified" if show_P else "overall_only"
        rows = []
        for r in src:
            entry = {"category": r["category"],
                     "total_n": r["n_total"], "total_pct": pct(r["n_total"], n)}
            if show_P:
                entry.update(P0_n=r["n_P0"], P0_pct=pct(r["n_P0"], n0),
                             P1_n=r["n_P1"], P1_pct=pct(r["n_P1"], n1))
            rows.append(entry)
        out_dims[dim] = rows
    return {
        "policy": "STEP83_INTERNAL_PUBLICATION_CANDIDATE_NOT_APPROVED",
        "source": "Step82 frozen restricted aggregate",
        "disclosure_notice": "NOT institutionally cleared; cross-table and cumulative review required",
        "source_warning_count": len(source_flags),
        "baseline_denominators": {"overall": n, "P0": n0, "P1": n1},
        "selection": {"retained_candidate_unique_patients": unique,
                      "scope": "retained date-valid I63-coded IMP keys only",
                      "grouping_policy": flow_policy,
                      "mutually_exclusive_patient_groups": flows},
        "dimension_policies": policies,
        "baseline": out_dims,
    }


def as_markdown(candidate):
    d = candidate["baseline_denominators"]
    lines = [
        "# Young Stroke: restricted reporting candidate",
        "",
        "**LOCAL REVIEW ONLY. NOT APPROVED FOR MANUSCRIPT RELEASE.**",
        "",
        "Data are from a previously filtered, date-valid I63-coded IMP encounter pool,",
        "not the complete network export. All results require cumulative disclosure review.",
        "",
        "## Cohort selection (mutually exclusive patients)",
        "",
        "| Stage or disposition | Patients |",
        "|---|---:|",
    ]
    for r in candidate["selection"]["mutually_exclusive_patient_groups"]:
        lines.append("| " + r["reason"] + " | " + format(r["n"], ",") + " |")
    lines += ["", "## Baseline characteristics", "",
              "Counts and percentages use the denominator shown in each column.",
              "", "| Characteristic | Category | Total (n=%s) | P=0 (n=%s) | P=1 (n=%s) |" %
              (format(d["overall"], ","), format(d["P0"], ","), format(d["P1"], ",")),
              "|---|---|---:|---:|---:|"]
    labels = {"SEX": "Source sex", "RACE": "Mapped race",
              "ETHNICITY": "Mapped ethnicity", "AGE_BAND": "Birth-year age band",
              "INDEX_YEAR": "Index admission year"}
    for dim in DIMS:
        for r in candidate["baseline"].get(dim, []):
            overall = "%s (%.2f%%)" % (format(r["total_n"], ","), r["total_pct"])
            if "P0_n" in r:
                p0 = "%s (%.2f%%)" % (format(r["P0_n"], ","), r["P0_pct"])
                p1 = "%s (%.2f%%)" % (format(r["P1_n"], ","), r["P1_pct"])
            else:
                p0 = p1 = "Not displayed"
            lines.append("| " + labels[dim] + " | " + r["category"] +
                         " | " + overall + " | " + p0 + " | " + p1 + " |")
        if candidate["dimension_policies"][dim] == "withheld_entire_dimension":
            lines.append("| " + labels[dim] + " | Withheld for disclosure review | " +
                         "Not displayed | Not displayed | Not displayed |")
    lines += ["",
              "The source P flag describes principal-I63 recording status, not a",
              "validated clinical stroke category. P-specific sex values are not displayed",
              "because withholding one small cell while retaining margins and companion",
              "cells could reveal it through subtraction. Missing and unmapped source",
              "labels remain distinct where available. Age bands are only assigned",
              "when both ages allowed by year of birth fall in the same category.",
              "", "No hospital-linked imaging validation or site clustering was performed.",
              "Do not merge these tables with other manuscript exhibits before",
              "an authorized cumulative/complementary disclosure review.", ""]
    return "\n".join(lines)


def _write_private(folder, artifacts):
    base = PRIVATE_ROOT.resolve()
    folder = Path(folder).expanduser().resolve()
    if base not in folder.parents or Path(folder).is_symlink():
        raise ValueError("Step83 output must stay inside local private results")
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(folder, 0o700)
    for name in artifacts:
        if (folder / name).exists() or (folder / name).is_symlink():
            raise FileExistsError("Existing Step83 output: " + name)
    written = []
    try:
        for name, content in artifacts.items():
            target = folder / name
            fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            written.append(target)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
    except BaseException:
        for target in written:
            target.unlink(missing_ok=True)
        raise
    return folder


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=STEP82)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--acknowledge", choices=[ACK], required=True)
    args = parser.parse_args(argv)
    if args.input.is_symlink() or not args.input.is_file():
        raise FileNotFoundError("Step82 frozen private aggregate is missing or a symlink")
    if PRIVATE_ROOT.resolve() not in args.input.resolve().parents:
        raise ValueError("Input must be inside local private results")
    source = json.loads(args.input.read_text(encoding="utf-8"))
    proposal = prepare(source)
    folder = _write_private(args.output_dir, {
        "reporting_candidate_LOCAL_ONLY.json": json.dumps(proposal, indent=2) + "\n",
        "reporting_candidate_LOCAL_ONLY.md": as_markdown(proposal),
    })
    print("STEP83 LOCAL ONLY: candidate prepared, not disclosure approved")
    print("Private output directory:", folder)
    print("Step82 flags independently verified:", proposal["source_warning_count"])
    print("SEX publication candidate policy:", proposal["dimension_policies"]["SEX"])
    print("Patient flow policy:", proposal["selection"]["grouping_policy"])
    print("All displayed category/denominator totals reconcile with frozen Step82 JSON")
    print("Do NOT upload, email, or commit private tables before institutional clearance")


if __name__ == "__main__":
    main()