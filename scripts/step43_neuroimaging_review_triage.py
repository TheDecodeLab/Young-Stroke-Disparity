#!/usr/bin/env python3
"""Step43: triage private Step42 terminology candidates without reading source ZIP.

Creates complete and balanced first-pass LOCAL-ONLY clinical review worksheets.
No candidate is accepted/rejected automatically. No clinical rows are read.
All outputs are restricted to the clone's gitignored results/phase1/.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import stat
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

if __package__:
    from .step42_neuroimaging_vocabulary import (
        PHASE1, ROOT, WORKSHEET as STEP42_CSV, REPORT as STEP42_JSON,
        FIELDS as STEP42_FIELDS, candidate_class,
    )
else:
    from step42_neuroimaging_vocabulary import (
        PHASE1, ROOT, WORKSHEET as STEP42_CSV, REPORT as STEP42_JSON,
        FIELDS as STEP42_FIELDS, candidate_class,
    )

FULL = "step43_neuroimaging_triage_full_LOCAL_ONLY.csv"
FIRST = "step43_neuroimaging_review_first_LOCAL_ONLY.csv"
REPORT = "step43_neuroimaging_triage_status.json"
REVIEW = "step43_neuroimaging_triage_status_REVIEW.zip"
EXTRA = (
    "triage_bucket_NOT_CLINICALLY_VALIDATED",
    "description_only_modality_anatomy_match",
    "suspected_nonprocedure_concept_FOR_REVIEW",
    "code_has_multiple_candidate_categories_FOR_REVIEW",
)
FIELDS = STEP42_FIELDS + EXTRA
BUCKET_ORDER = (
    "A_historical_CPT_anchor",
    "B_description_specific",
    "C_description_disagrees_with_path",
    "D_path_only_or_weak_description",
    "E_mixed_head_and_neck",
    "F_possible_nonprocedure_concept",
    "G_same_code_multiple_categories",
)
REVIEW_WARNING = re.compile(
    r"\b(history of|personal history|family history|refus(?:ed|al)|declin(?:ed|ed)|"
    r"contraindicat(?:ion|ed)|screening for|interpretation of|"
    r"result of|abnormal result|finding of|documentation of|"
    r"request for|order for|planned|counseling about|"
    r"not performed|follow up after)\b", re.I,
)


def private_path(path: Path) -> Path:
    allowed = ROOT.resolve() / "results" / "phase1"
    if PHASE1.resolve() != allowed:
        raise ValueError("results/phase1 must not escape the cloned repo")
    actual = path.expanduser().resolve()
    if actual != allowed and allowed not in actual.parents:
        raise ValueError("Input and output must stay in cloned repository results/phase1/")
    return actual


def read_inputs(worksheet: Path, status: Path):
    status_blob = status.read_bytes()
    status_json = json.loads(status_blob)
    if status_json.get("stage") != "STEP42_REFERENCE_ONLY_NEUROIMAGING_CODE_DISCOVERY":
        raise ValueError("Missing Step42 reference-only provenance")
    if status_json.get("clinical_event_rows_examined") != 0:
        raise ValueError("Step42 source is not reference-only")
    with worksheet.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != STEP42_FIELDS:
            raise ValueError("Unexpected Step42 CSV header or field ordering")
        rows = list(reader)
    if len(rows) != status_json.get("candidate_rows_n"):
        raise ValueError("Step42 codebook row count mismatch")
    categories = Counter(row["candidate_category_NOT_VALIDATED"] for row in rows)
    reasons = Counter(row["discovery_reason"] for row in rows)
    if dict(categories) != status_json.get("candidate_category_rows"):
        raise ValueError("Step42 category totals inconsistent with worksheet")
    if dict(reasons) != status_json.get("discovery_reason_rows"):
        raise ValueError("Step42 discovery totals inconsistent with worksheet")
    return rows, status_blob


def triage_rows(rows):
    code_categories = defaultdict(set)
    for row in rows:
        code_categories[(row["code_system"].strip().upper(), row["code"].strip())].add(
            row["candidate_category_NOT_VALIDATED"]
        )
    categorized = []
    for row in rows:
        desc = row["code_description"]
        path = row["path"]
        original = row["candidate_category_NOT_VALIDATED"]
        match = candidate_class(row["code_system"], row["code"], desc, "")
        description_category = match[0] if match else "NONE"
        possible_nonprocedure = bool(REVIEW_WARNING.search(desc))
        multiple = len(code_categories[(row["code_system"].strip().upper(), row["code"].strip())]) > 1
        if multiple:
            tier = "G_same_code_multiple_categories"
        elif possible_nonprocedure:
            tier = "F_possible_nonprocedure_concept"
        elif original == "AMBIGUOUS_HEAD_AND_NECK":
            tier = "E_mixed_head_and_neck"
        elif row["discovery_reason"] == "historical_cpt14_anchor":
            tier = "A_historical_CPT_anchor"
        elif description_category == original:
            tier = "B_description_specific"
        elif description_category != "NONE":
            tier = "C_description_disagrees_with_path"
        else:
            tier = "D_path_only_or_weak_description"
        record = dict(row)
        record.update({
            "triage_bucket_NOT_CLINICALLY_VALIDATED": tier,
            "description_only_modality_anatomy_match": description_category,
            "suspected_nonprocedure_concept_FOR_REVIEW": "yes" if possible_nonprocedure else "no",
            "code_has_multiple_candidate_categories_FOR_REVIEW": "yes" if multiple else "no",
        })
        categorized.append(record)
    return sorted(categorized, key=lambda r: (
        BUCKET_ORDER.index(r["triage_bucket_NOT_CLINICALLY_VALIDATED"]),
        r["candidate_category_NOT_VALIDATED"],
        r["code_system"], r["code"], r["code_description"],
    ))


def review_first(rows, per_category=15):
    """Balanced small review SAMPLE; not a clinical inclusions list."""
    counts = Counter()
    selected = []
    for row in rows:
        key = row["candidate_category_NOT_VALIDATED"]
        if counts[key] < per_category:
            selected.append(row)
            counts[key] += 1
    return selected


def atomic_bytes(path, blob: bytes):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".step43_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(blob)
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def safe_spreadsheet_cell(value):
    """Avoid spreadsheet formula execution in generated review-only CSV cells."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def csv_bytes(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: safe_spreadsheet_cell(value) for key, value in row.items()})
    return buffer.getvalue().encode("utf-8")


def make_review_zip(path, report):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".step43zip_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream, zipfile.ZipFile(
            stream, "w", compression=zipfile.ZIP_DEFLATED
        ) as z:
            z.write(report, arcname=REPORT)
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run(worksheet=PHASE1 / STEP42_CSV, status=PHASE1 / STEP42_JSON,
        output_dir=PHASE1, per_category=15, overwrite=False):
    if not 1 <= per_category <= 50:
        raise ValueError("--review-per-category must be 1..50")
    source = private_path(worksheet)
    status_path = private_path(status)
    out = private_path(output_dir)
    targets = [out / name for name in (FULL, FIRST, REPORT, REVIEW)]
    if len(set([source, status_path] + targets)) != len([source, status_path] + targets):
        raise ValueError("Step43 inputs must not collide with output paths")
    if not overwrite and any(t.exists() for t in targets):
        raise FileExistsError(
            "Step43 output exists: preserve clinical annotations and use --overwrite explicitly"
        )
    rows, status_blob = read_inputs(source, status_path)
    grouped = triage_rows(rows)
    initial = review_first(grouped, per_category)
    if len(grouped) != len(rows):
        raise ValueError("Triage did not preserve source rows")
    count_tier = Counter(r["triage_bucket_NOT_CLINICALLY_VALIDATED"] for r in grouped)
    prior_categories = Counter(r["candidate_category_NOT_VALIDATED"] for r in rows)
    first_categories = Counter(r["candidate_category_NOT_VALIDATED"] for r in initial)
    report = {
        "stage": "STEP43_REFERENCE_CODEBOOK_REVIEW_TRIAGE",
        "input_step42_sha256": hashlib.sha256(status_blob).hexdigest(),
        "clinical_event_rows_examined": 0,
        "source_candidate_rows": len(rows),
        "all_candidate_rows_preserved_in_private_full_worksheet": True,
        "review_first_is_nonrepresentative_convenience_subset": True,
        "review_per_category_cap": per_category,
        "review_first_rows_n": len(initial),
        "review_backlog_rows_n": len(rows) - len(initial),
        "review_first_category_counts": dict(sorted(first_categories.items())),
        "full_candidate_category_counts": dict(sorted(prior_categories.items())),
        "triage_bucket_counts": dict(sorted(count_tier.items())),
        "patient_or_encounter_identifiers_exported": False,
        "raw_code_values_or_descriptions_exported": False,
        "clinical_code_approval_provided": False,
        "ready_for_imaging_outcome_ascertainment": False,
        "notes": [
            "Heuristics rank only the manual review workload; no code is accepted or rejected.",
            "Path-only terminology matches and nonprocedure concepts require special review.",
            "The first-review worksheet is NOT complete and MUST NOT be used as the final code list.",
            "Review all source code systems, including possible missed terminology, before full extraction.",
            "The source CSV and generated detailed worksheets are local-only and never included in the ZIP.",
        ],
    }
    atomic_bytes(out / FULL, csv_bytes(grouped))
    atomic_bytes(out / FIRST, csv_bytes(initial))
    atomic_bytes(out / REPORT, (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    make_review_zip(out / REVIEW, out / REPORT)
    print("Step43 private terminology-review triage completed; clinical records read: 0.")
    print("Full local worksheet (DO NOT UPLOAD):", out / FULL)
    print("First local review worksheet (DO NOT UPLOAD):", out / FIRST)
    print("Aggregate-only review ZIP:", out / REVIEW)
    print("No neuroimaging code inclusion/clinical approval inferred.")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--step42-csv", type=Path, default=PHASE1 / STEP42_CSV)
    p.add_argument("--step42-json", type=Path, default=PHASE1 / STEP42_JSON)
    p.add_argument("--output-dir", type=Path, default=PHASE1)
    p.add_argument("--review-per-category", type=int, default=15)
    p.add_argument("--overwrite", action="store_true", help="Deliberately replace previous review files")
    a = p.parse_args()
    run(a.step42_csv, a.step42_json, a.output_dir, a.review_per_category, a.overwrite)


if __name__ == "__main__":
    main()
