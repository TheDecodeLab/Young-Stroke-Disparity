#!/usr/bin/env python3
"""Step50: inspect Step36 structural metadata for possible encounter linkage keys.

No ZIP access, no table-row reads, no patient identifiers, and no inferred HCO
mapping. The output is an owner-only PRIVATE metadata/review package inside
the actual cloned repository's ignored results/phase1/ directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE1 = ROOT / "results" / "phase1"
PREFLIGHT = PHASE1 / "step36_research_metadata_preflight.json"
PRIVATE = PHASE1 / "full_reconstruction_private" / "site_linkage_review"
REPORT = PRIVATE / "step50_site_linkage_metadata_LOCAL_ONLY.json"
REVIEW = PRIVATE / "site_linkage_steward_review_LOCAL_ONLY.json"
REQUIRED = ("encounter.csv", "diagnosis.csv", "procedure.csv", "patient.csv")
KEYS = ("patient_id", "encounter_id", "start_date", "end_date", "type")
STRONG_HINTS = frozenset({
    "hco_id", "hco_identifier", "site_id", "facility_id", "hospital_id",
    "organization_id", "care_site_id", "healthcare_organization_id",
    "healthcare_organization_identifier", "data_partner_id",
    "parent_encounter_id", "parent_visit_id", "episode_id", "visit_group_id",
    "admission_id", "hospitalization_id", "visit_occurrence_id",
})
WEAK_HINTS = frozenset({
    "source_id", "origin_id", "external_id", "location_id", "location",
    "provider_id", "source_system", "site", "hco", "facility",
})


def owner_path(path: Path) -> Path:
    base = ROOT.resolve() / "results" / "phase1"
    if PHASE1.resolve() != base:
        raise ValueError("Private results/phase1 path is a symlink escape")
    actual = path.expanduser().resolve()
    if actual != base and base not in actual.parents:
        raise ValueError("All inputs and outputs must be inside cloned repo results/phase1/")
    return actual


def classify_field(name):
    """Field spelling is a weak structural hint, never proof of field semantics."""
    field = str(name).strip().lower()
    if field in STRONG_HINTS:
        return "possible_hco_or_episode_key_REQUIRES_VERIFICATION"
    if field in WEAK_HINTS:
        return "generic_or_source_key_NOT_AN_APPROVED_SITE_IDENTIFIER"
    return None


def evaluate_step36(preflight: dict) -> dict:
    if (preflight.get("stage") != "STEP36_RESEARCH_METADATA_PREFLIGHT" or
            preflight.get("clinical_rows_read") != 0 or
            preflight.get("full_clinical_tables_scanned") is not False):
        raise ValueError("Step36 provenance must confirm metadata-only, zero clinical rows")
    files = preflight.get("files")
    if not isinstance(files, dict):
        raise ValueError("Step36 files metadata is missing")
    outputs = {}
    warnings = []
    for table in REQUIRED:
        data = files.get(table)
        if not isinstance(data, dict) or data.get("present") is not True:
            raise ValueError("Step36 required table missing: " + table)
        raw_headers = data.get("headers")
        if not isinstance(raw_headers, list) or not all(isinstance(x,str) for x in raw_headers):
            raise ValueError("Step36 table headers missing: " + table)
        if len(set(raw_headers)) != len(raw_headers):
            warnings.append("duplicate_header_names_" + table)
        seen = [{"column": name, "hint_NOT_VALIDATION": classify_field(name)}
                for name in raw_headers if classify_field(name)]
        outputs[table] = {
            "header_count": len(raw_headers),
            "candidate_linkage_field_names": seen,
            "patient_id_present": "patient_id" in raw_headers,
            "encounter_id_present": "encounter_id" in raw_headers,
        }
        if table == "encounter.csv":
            outputs[table]["date_and_type_columns_present"] = {
                key: key in raw_headers for key in KEYS[2:]
            }
    encounter_fields = {x["column"].strip().lower()
                        for x in outputs["encounter.csv"]["candidate_linkage_field_names"]}
    non_source_candidates = sorted(k for k in encounter_fields if k in STRONG_HINTS)
    return {
        "stage": "STEP50_SITE_AND_EPISODE_METADATA_ONLY",
        "clinical_rows_read": 0,
        "source_zip_accessed": False,
        "actual_hco_id_verified": False,
        "true_ED_IP_episode_linkage_verified": False,
        "source_id_can_be_used_as_site_key": False,
        "study_real_data_scan_approved": False,
        "source_step36_structural_preflight_supports_linkage":
            preflight.get("schema_supports_attempted_encounter_linkage") is True,
        "table_field_hints": outputs,
        "encounter_possible_hco_or_episode_columns": non_source_candidates,
        "source_id_if_present_remains_unverified": "source_id" in encounter_fields,
        "warnings": warnings,
        "next_requirement": "Data-steward review of exact encounter/HCO key meanings, scope and missingness; metadata-only report is insufficient",
    }


def atomic_json(path, obj):
    path = owner_path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if parent.stat().st_mode & 0o077:
        raise PermissionError("Private site linkage directory must have mode 0700")
    if path.exists():
        raise FileExistsError("Existing private Step50 file; refusing to overwrite possible annotations")
    fd, temp = tempfile.mkstemp(prefix=".step50_", dir=str(parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.write("\n")
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        # Refuse overwrite if file appeared after initial existence check.
        os.link(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def prepare(preflight_path=PREFLIGHT, output_dir=PRIVATE):
    src = owner_path(preflight_path)
    dst = owner_path(output_dir)
    report_path = dst / REPORT.name
    review_path = dst / REVIEW.name
    if report_path.exists() or review_path.exists():
        raise FileExistsError("Step50 output already exists: annotations will not be overwritten")
    payload = src.read_bytes()
    obj = json.loads(payload)
    report = evaluate_step36(obj)
    report["source_step36_sha256"] = hashlib.sha256(payload).hexdigest()
    review = {
        "reviewer_name": "", "review_date": "", "approval_reference": "",
        "source_step36_sha256": report["source_step36_sha256"],
        "verified_same_hco_key_name": "",
        "verified_parent_episode_key_name": "",
        "documented_mapping_reference": "",
        "patient_id_scope_confirmed": False,
        "encounter_id_scope_confirmed": False,
        "same_hco_mapping_confirmed": False,
        "ED_EMER_and_IP_IMP_meaning_confirmed": False,
        "date_only_linkage_policy_confirmed": False,
        "notes_on_transfers_duplicates_missing_site_values": "",
        "NOTE": "Blank means NOT approved. Metadata column names never establish identity, linkage accuracy or permission to scan.",
    }
    atomic_json(report_path, report)
    atomic_json(review_path, review)
    print("STEP50 METADATA ONLY: inspected existing Step36 field names.")
    print("Potential HCO/episode columns in encounter.csv:",
          ", ".join(report["encounter_possible_hco_or_episode_columns"]) or "none identified")
    print("source_id remains unverified as a site identifier.")
    print("Local private report:", report_path)
    print("Local blank steward worksheet:", review_path)
    print("Clinical rows read: 0. Site/episode linkage NOT verified. Full scan BLOCKED.")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, default=PREFLIGHT)
    args = parser.parse_args()
    prepare(args.preflight)


if __name__ == "__main__":
    main()
