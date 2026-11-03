#!/usr/bin/env python3
"""Step 38: bounded Research Network encounter-type terminology audit.

Read only a bounded encounter.csv prefix plus one streaming pass over
standardized_terminology.csv (reference metadata, not patient events).
Outputs are coarse aggregate-only inside gitignored results/phase1/.
No encounter/patient/source IDs, raw type codes, or clinical events exported.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import os
import re
import stat
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE1 = ROOT / "results" / "phase1"
STEP36 = PHASE1 / "step36_research_metadata_preflight.json"
STEP37 = PHASE1 / "step37_research_encounter_pilot.json"
REPORT = "step38_encounter_type_terminology.json"
REVIEW = "step38_encounter_type_terminology_review.zip"
SMALL = "suppressed_1_to_10"
REQUIRED_TERMS = {"code_system", "code", "code_description", "path"}
REQUIRED_ENCOUNTERS = {"type"}


def suppress(n):
    return SMALL if 0 < n < 11 else n


def member_paths(archive):
    mapping = {}
    for member in archive.infolist():
        if member.is_dir():
            continue
        basename = member.filename.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if basename in ("encounter.csv", "standardized_terminology.csv"):
            if basename in mapping:
                raise ValueError("Duplicate archive member: " + basename)
            mapping[basename] = member.filename
    if len(mapping) != 2:
        raise ValueError("Both encounter.csv and standardized_terminology.csv are required")
    return mapping


def normalize_type(value):
    return re.sub(r"\s+", " ", (value or "").strip()).upper()


def category_from_text(value):
    """Lexical *candidate* classification, not an approved encounter ontology."""
    text = (value or "").lower()
    matches = []
    predicates = (
        ("inpatient_candidate", ("inpatient", "in-patient", "hospital admission", "hospitalization")),
        ("emergency_candidate", ("emergency", "emergent", "emergency department")),
        ("observation_candidate", ("observation", "observational stay")),
        ("outpatient_candidate", ("outpatient", "out-patient", "ambulatory", "office visit")),
        ("virtual_candidate", ("telehealth", "telemedicine", "virtual visit")),
    )
    for category, phrases in predicates:
        if any(word in text for word in phrases):
            matches.append(category)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return "mixed_candidate"
    return "unclassified"


def read_encounter_types(archive, member, limit):
    counts = Counter()
    total = 0
    with archive.open(member) as raw:
        with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not REQUIRED_ENCOUNTERS.issubset(reader.fieldnames or []):
                raise ValueError("encounter.csv is missing type header")
            for row in itertools.islice(reader, limit):
                counts[normalize_type(row.get("type"))] += 1
                total += 1
    return counts, total


def reference_lookup(archive, member, desired, cap):
    found = defaultdict(set)
    terminology_rows = 0
    encounter_terms = 0
    with archive.open(member) as raw:
        with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not REQUIRED_TERMS.issubset(reader.fieldnames or []):
                raise ValueError("standardized_terminology.csv missing expected fields")
            for row in reader:
                if terminology_rows >= cap:
                    raise ValueError("Terminology scan cap reached; do not report incomplete mapping")
                terminology_rows += 1
                system = normalize_type(row.get("code_system")).replace("_", " ")
                if system != "ENCOUNTER TYPE":
                    continue
                encounter_terms += 1
                code = normalize_type(row.get("code"))
                if code in desired:
                    # Keep labels transient and only emit safe broad categories.
                    candidate = category_from_text(
                        (row.get("code_description") or "") + " " + (row.get("path") or "")
                    )
                    found[code].add(candidate)
    return found, terminology_rows, encounter_terms


def summarise(types, term_map):
    categories = Counter()
    sources = Counter()
    for code, count in types.items():
        if not code:
            sources["missing_type"] += count
            categories["missing_type"] += count
            continue
        reference_categories = term_map.get(code, set())
        if not reference_categories:
            sources["no_reference_match"] += count
            # This fallback is only lexical, not a valid clinical mapping.
            heuristic = category_from_text(code)
            categories[heuristic if heuristic == "unclassified" else "lexical_" + heuristic] += count
        else:
            sources["mapped_to_encounter_type_terminology"] += count
            if len(reference_categories) != 1:
                categories["ambiguous_reference_mapping"] += count
            else:
                label = next(iter(reference_categories))
                categories["terminology_" + label] += count
    return (
        {key: suppress(value) for key, value in sorted(categories.items())},
        {key: suppress(value) for key, value in sorted(sources.items())},
    )


def secure_directory(path):
    expected = ROOT.resolve() / "results" / "phase1"
    if PHASE1.resolve() != expected:
        raise ValueError("results/phase1 directory may not be a symlink escape")
    resolved = path.expanduser().resolve()
    if resolved != expected and expected not in resolved.parents:
        raise ValueError("Generated output must be within cloned repository results/phase1/")
    return resolved


def save_private_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp_path = tempfile.mkstemp(prefix=".step38_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as writer:
            json.dump(payload, writer, indent=2, sort_keys=True)
            writer.write("\n")
        os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def save_private_zip(path, report_path):
    fd, temp_path = tempfile.mkstemp(prefix=".step38zip_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as writer:
            with zipfile.ZipFile(writer, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.write(report_path, arcname=REPORT)
        os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def run(source, prior36_path=STEP36, prior37_path=STEP37,
        output_dir=PHASE1, max_encounters=50000, max_terms=3000000):
    if not (1 <= max_encounters <= 200000):
        raise ValueError("max encounters must be in 1..200000")
    if not (1 <= max_terms <= 3000000):
        raise ValueError("max terminology rows must be in 1..3000000")
    output = secure_directory(output_dir)
    report_path, zip_path = output / REPORT, output / REVIEW
    input_path = source.expanduser().resolve()
    if input_path in (report_path, zip_path):
        raise ValueError("Source ZIP path cannot be an output")
    blob36, blob37 = prior36_path.read_bytes(), prior37_path.read_bytes()
    p36, p37 = json.loads(blob36), json.loads(blob37)
    if p36.get("stage") != "STEP36_RESEARCH_METADATA_PREFLIGHT" or not p36.get("schema_supports_attempted_encounter_linkage"):
        raise ValueError("Step36 structural readiness report is invalid")
    if p37.get("stage") != "STEP37_RESEARCH_ENCOUNTER_BOUNDED_PILOT" or p37.get("input_step36_sha256") != hashlib.sha256(blob36).hexdigest():
        raise ValueError("Step37 results do not match Step36 input")
    with zipfile.ZipFile(input_path) as archive:
        members = member_paths(archive)
        prior_file = p36.get("files", {}).get("encounter.csv", {})
        if prior_file.get("uncompressed_bytes") != archive.getinfo(members["encounter.csv"]).file_size:
            raise ValueError("Encounter file size differs from Step36")
        types, n = read_encounter_types(archive, members["encounter.csv"], max_encounters)
        if n != p37.get("source_tables", {}).get("encounter.csv", {}).get("rows_examined"):
            raise ValueError("Encounter prefix count differs from Step37; rerun with matching limit")
        mapping, ref_rows, terms = reference_lookup(
            archive, members["standardized_terminology.csv"], set(types), max_terms
        )
    groups, lookup_coverage = summarise(types, mapping)
    report = {
        "stage": "STEP38_ENCOUNTER_TYPE_REFERENCE_PILOT",
        "input_step36_sha256": hashlib.sha256(blob36).hexdigest(),
        "input_step37_sha256": hashlib.sha256(blob37).hexdigest(),
        "encounter_rows_examined": n,
        "nonrandom_prefix_only": True,
        "terminology_rows_examined": ref_rows,
        "encounter_type_reference_rows_found": terms,
        "distinct_encounter_type_values_in_prefix": len(types),
        "encounter_type_lookup_coverage": lookup_coverage,
        "encounter_category_candidate_counts": groups,
        "raw_encounter_type_values_exported": False,
        "individual_patient_encounter_or_source_ids_exported": False,
        "encounter_type_clinically_validated": False,
        "ready_for_disparity_analysis": False,
        "interpretation": [
            "The encountered type values are looked up only against local Encounter Type reference terminology.",
            "Descriptions are classified by keyword only; code meanings and hospital admission criteria require clinical review.",
            "No representative prevalence or source-wide linkage estimate can be obtained from these prefixes.",
            "The 2.3M-row terminology stream is reference metadata, not a clinical-event scan.",
            "Review aggregate sharing permissions and complementary disclosure before uploading review ZIP.",
        ],
    }
    save_private_json(report_path, report)
    save_private_zip(zip_path, report_path)
    print("Step38 terminology pilot completed; no full clinical-event scan.")
    print("Encounter-prefix rows:", n, "| terminology rows:", ref_rows)
    print("Aggregate report:", report_path)
    print("Review ZIP:", zip_path)
    print("Inpatient meaning and suitability for disparity analysis remain UNVERIFIED.")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", required=True, type=Path)
    p.add_argument("--step36-json", type=Path, default=STEP36)
    p.add_argument("--step37-json", type=Path, default=STEP37)
    p.add_argument("--output-dir", type=Path, default=PHASE1)
    p.add_argument("--max-encounters", type=int, default=50000)
    p.add_argument("--max-terminology-rows", type=int, default=3000000)
    a = p.parse_args()
    run(a.zip, a.step36_json, a.step37_json, a.output_dir,
        a.max_encounters, a.max_terminology_rows)


if __name__ == "__main__":
    main()
