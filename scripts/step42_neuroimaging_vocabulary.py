#!/usr/bin/env python3
"""Step42: local, reference-only neuroimaging vocabulary discovery.

Scans standardized_terminology.csv inside the existing Research Network ZIP,
not the patient/encounter/diagnosis/procedure clinical tables. Generates a
PRIVATE, unapproved candidate codebook and a separate aggregate-only ZIP.
All generated output remains in the clone's gitignored results/phase1/.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import stat
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE1 = ROOT / "results" / "phase1"
WORKSHEET = "step42_neuroimaging_codebook_LOCAL_ONLY.csv"
REPORT = "step42_neuroimaging_vocabulary_status.json"
REVIEW_ZIP = "step42_neuroimaging_vocabulary_status_REVIEW.zip"
ALLOWED_SYSTEMS = {"CPT", "HCPCS", "SNOMED", "ICD-10-PCS", "ICD-9-CM"}
REQUIRED = {"code_system", "code", "code_description", "path"}
FIELDS = (
    "code_system", "code", "code_description", "path",
    "candidate_category_NOT_VALIDATED", "discovery_reason",
    "reviewer_include_LEAVE_BLANK", "reviewer_notes_LEAVE_BLANK",
)
CPT_ANCHORS = {
    **{k: "CT_HEAD" for k in ("70450", "70460", "70470")},
    "70496": "CTA_HEAD",
    "70498": "CTA_NECK",
    **{k: "MRI_BRAIN" for k in ("70551", "70552", "70553")},
    **{k: "MRA_HEAD" for k in ("70544", "70545", "70546")},
    **{k: "MRA_NECK" for k in ("70547", "70548", "70549")},
}
HEAD = re.compile(r"\b(brain|head|intracranial|cerebral|cranial|cranium)\b", re.I)
NECK = re.compile(r"\b(neck|carotid|cervical|extracranial)\b", re.I)
CTA = re.compile(
    r"\b(cta|ct angiograph(?:y|ic)|computed tomograph(?:y|ic) angiograph(?:y|ic)|"
    r"computed tomographic angiograph(?:y|ic))\b", re.I
)
MRA = re.compile(
    r"\b(mra|mr angiograph(?:y|ic)|magnetic resonance angiograph(?:y|ic))\b", re.I
)
MRI = re.compile(
    r"\b(mri|mr imaging|magnetic resonance imag(?:e|ing)|"
    r"magnetic resonance imaging)\b", re.I
)
CT = re.compile(
    r"\b(ct|ct scan|computed tomograph(?:y|ic))\b", re.I
)


def candidate_class(system: str, code: str, description: str, path: str):
    """For discovery only: no positive candidate implies completed imaging."""
    system = (system or "").strip().upper()
    code = (code or "").strip()
    if system == "CPT" and code in CPT_ANCHORS:
        return CPT_ANCHORS[code], "historical_cpt14_anchor"
    text = re.sub(r"[\s_/]+", " ", f"{description or ''} {path or ''}")
    head, neck = bool(HEAD.search(text)), bool(NECK.search(text))
    if not (head or neck):
        return None
    modality = ("MRA" if MRA.search(text) else
                "CTA" if CTA.search(text) else
                "MRI" if MRI.search(text) else
                "CT" if CT.search(text) else None)
    if modality is None:
        return None
    if head and neck:
        return "AMBIGUOUS_HEAD_AND_NECK", "textual_candidate_needs_anatomy_review"
    if modality == "MRI":
        return ("MRI_BRAIN", "textual_candidate") if head else None
    if modality == "CT":
        return ("CT_HEAD", "textual_candidate") if head else None
    return f"{modality}_{'HEAD' if head else 'NECK'}", "textual_candidate"


def reference_member(z):
    found = []
    for info in z.infolist():
        if info.is_dir():
            continue
        if info.filename.replace("\\", "/").rsplit("/", 1)[-1].lower() == "standardized_terminology.csv":
            found.append(info.filename)
    if len(found) != 1:
        raise ValueError("Expected exactly one standardized_terminology.csv member")
    return found[0]


def scan_reference(z, member, maximum_rows=3_000_000, maximum_candidates=20_000):
    rows_examined = 0
    candidates = []
    code_system_counts = Counter()
    candidate_counts = Counter()
    reasons = Counter()
    seen = set()
    with z.open(member) as binary, io.TextIOWrapper(
        binary, encoding="utf-8-sig", newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError("Reference table missing required codebook columns")
        for record in reader:
            if rows_examined >= maximum_rows:
                raise ValueError("Terminology row limit exceeded; do not report partial discovery")
            rows_examined += 1
            system = (record.get("code_system") or "").strip().upper()
            if system not in ALLOWED_SYSTEMS:
                continue
            code_system_counts[system] += 1
            code = (record.get("code") or "").strip()
            if not code:
                continue
            desc = (record.get("code_description") or "").strip()
            path = (record.get("path") or "").strip()
            category = candidate_class(system, code, desc, path)
            if not category:
                continue
            key = (system, code, desc, path, category[0])
            if key in seen:
                continue
            seen.add(key)
            if len(candidates) >= maximum_candidates:
                raise ValueError("Too many terminology candidates; tighten codebook rules")
            candidates.append({
                "code_system": system,
                "code": code,
                "code_description": desc,
                "path": path,
                "candidate_category_NOT_VALIDATED": category[0],
                "discovery_reason": category[1],
                "reviewer_include_LEAVE_BLANK": "",
                "reviewer_notes_LEAVE_BLANK": "",
            })
            candidate_counts[category[0]] += 1
            reasons[category[1]] += 1
    return {
        "terminology_rows_examined": rows_examined,
        "source_system_rows": dict(sorted(code_system_counts.items())),
        "candidate_category_rows": dict(sorted(candidate_counts.items())),
        "discovery_reason_rows": dict(sorted(reasons.items())),
        "candidate_rows_n": len(candidates),
    }, candidates


def private_dir(directory):
    root_expected = ROOT.resolve() / "results" / "phase1"
    if PHASE1.resolve() != root_expected:
        raise ValueError("The results/phase1 location cannot be a symlink escape")
    path = directory.expanduser().resolve()
    if path != root_expected and root_expected not in path.parents:
        raise ValueError("Output must be inside the cloned repository results/phase1/")
    return path


def atomic_file(path, write_fn):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(dir=str(path.parent), prefix=".step42_")
    try:
        with os.fdopen(fd, "wb") as f:
            write_fn(f)
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def save_json(path, content):
    def writer(f):
        f.write((json.dumps(content, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    atomic_file(path, writer)


def save_csv(path, candidates):
    def writer(f):
        text = io.StringIO(newline="")
        w = csv.DictWriter(text, FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(candidates)
        f.write(text.getvalue().encode("utf-8"))
    atomic_file(path, writer)


def save_zip(path, report):
    def writer(f):
        with zipfile.ZipFile(f, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.write(report, arcname=REPORT)
    atomic_file(path, writer)


def run(source_zip, output_directory=PHASE1, max_rows=3_000_000,
        max_candidates=20_000):
    if not 1 <= max_rows <= 3_000_000:
        raise ValueError("--max-terminology-rows must be 1..3000000")
    if not 1 <= max_candidates <= 20_000:
        raise ValueError("--max-candidates must be 1..20000")
    dest = private_dir(output_directory)
    csv_path, json_path, zip_path = (
        dest / WORKSHEET, dest / REPORT, dest / REVIEW_ZIP,
    )
    if source_zip.expanduser().resolve() in (csv_path.resolve(), json_path.resolve(), zip_path.resolve()):
        raise ValueError("Input ZIP must not overwrite an output file")
    with zipfile.ZipFile(source_zip) as z:
        member = reference_member(z)
        if z.getinfo(member).file_size > 500_000_000:
            raise ValueError("Terminology file unexpectedly large; check source")
        counts, candidates = scan_reference(z, member, max_rows, max_candidates)
    # Write worksheet privately and NEVER include it inside review ZIP.
    # Treat discovered rows as raw reference metadata requiring clinical review.
    candidates.sort(key=lambda r: (
        r["candidate_category_NOT_VALIDATED"], r["code_system"], r["code"],
    ))
    payload = {
        "stage": "STEP42_REFERENCE_ONLY_NEUROIMAGING_CODE_DISCOVERY",
        "source_is_reference_terminology_only": True,
        "clinical_event_rows_examined": 0,
        "max_terminology_rows_cap": max_rows,
        "review_needed": True,
        "historical_cpt14_is_not_a_validated_imaging_codebook": True,
        "snomed_hcpcs_icd_procedure_coverage_not_validated": True,
        "patient_or_encounter_identifiers_exported": False,
        "raw_terminology_codes_or_descriptions_in_review_zip": False,
        "ready_for_cohort_imaging_ascertainment": False,
        "warnings": [
            "Keyword discovery produces false positives and can miss clinically important terms.",
            "Reference availability does not prove any code occurred in the clinical export.",
            "Category assignment is a review suggestion, not evidence of a completed scan.",
            "Local CSV contains raw reference metadata and must not be committed/uploaded without approval.",
        ],
        **counts,
    }
    save_csv(csv_path, candidates)
    save_json(json_path, payload)
    save_zip(zip_path, json_path)
    print("Step42 reference terminology discovery completed; clinical records read: 0.")
    print("Private worksheet (DO NOT UPLOAD):", csv_path)
    print("Aggregate-only review ZIP:", zip_path)
    print("Codebook remains unapproved. No disparity analysis authorized.")
    return payload


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", required=True, type=Path)
    p.add_argument("--output-dir", default=PHASE1, type=Path)
    p.add_argument("--max-terminology-rows", default=3_000_000, type=int)
    p.add_argument("--max-candidates", default=20_000, type=int)
    args = p.parse_args()
    run(args.zip, args.output_dir, args.max_terminology_rows, args.max_candidates)


if __name__ == "__main__":
    main()
