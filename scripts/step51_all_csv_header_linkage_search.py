#!/usr/bin/env python3
"""Step51: all-CSV HEADER-ONLY locator for hospital/episode field candidates.

The user supplies the local read-only Research Network ZIP. This script reads
the ZIP central directory and the first CSV header line of each CSV member.
It NEVER reads clinical DATA rows, extracts files, scans tables, or infers
that source_id (or any field spelling) proves HCO/episode identity.
All output is private in the clone's Git-ignored results/phase1/ directory.
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
from collections import Counter
from pathlib import Path

try:
    from .step50_site_linkage_metadata_check import (
        ROOT, PHASE1, PREFLIGHT, PRIVATE, STRONG_HINTS, WEAK_HINTS,
        owner_path,
    )
except ImportError:
    from step50_site_linkage_metadata_check import (
        ROOT, PHASE1, PREFLIGHT, PRIVATE, STRONG_HINTS, WEAK_HINTS,
        owner_path,
    )

OUTPUT = PRIVATE / "step51_all_csv_header_linkage_hints_LOCAL_ONLY.json"
MAX_MEMBERS = 250
MAX_HEADER = 128 * 1024
MAX_COLUMNS = 1024
CORE = ("encounter.csv", "diagnosis.csv", "procedure.csv", "patient.csv")
TERMS = frozenset({
    "hospital", "hco", "facility", "organization", "organisation",
    "site", "episode", "admission", "encounter", "visit", "transfer",
    "parent", "care", "location",
})


def clean_basename(name):
    """Avoid reflecting arbitrary ZIP directories/member paths in report."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", base):
        raise ValueError("CSV member basename contains unexpected characters")
    return base.lower()


def field_hint(name):
    """Field-name clue only, NOT clinical/data-steward validation."""
    val = name.strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", val.lower()).strip("_")
    if normalized in ("patient_id", "encounter_id", "visit_id", "date", "type"):
        return None
    if normalized in WEAK_HINTS or normalized in {
        "origin", "origin_code", "source", "source_identifier",
        "source_record_id", "record_source", "data_source_id",
    }:
        return "generic_source_OR_location_NOT_SITE_VALIDATED"
    if normalized in STRONG_HINTS:
        return "possible_hco_OR_episode_key_NOT_VALIDATED"
    tokens = set(filter(None, normalized.split("_")))
    if tokens & {"hco", "hospital", "facility", "site", "episode", "admission"}:
        return "name_suggests_hco_OR_episode_REQUIRES_STEWARD_REVIEW"
    if "parent" in tokens and tokens & {"encounter", "visit", "event"}:
        return "possible_parent_encounter_REQUIRES_STEWARD_REVIEW"
    if tokens & {"organization", "organisation"} and tokens & {
        "id", "key", "code", "identifier", "source"
    }:
        return "possible_organization_key_REQUIRES_STEWARD_REVIEW"
    if "transfer" in tokens and tokens & {"id", "key", "from", "to", "site"}:
        return "possible_transfer_key_REQUIRES_STEWARD_REVIEW"
    return None


def header_from_member(z, member, max_header=MAX_HEADER):
    # Exactly one physical line. A quoted multiline CSV header is refused:
    # attempting to parse subsequent lines could cross into clinical rows.
    with z.open(member) as raw:
        first = raw.readline(max_header + 1)
    if not first.endswith(b"\n") or len(first) > max_header:
        raise ValueError("CSV header missing newline or exceeds safe header limit")
    decoded = first.decode("utf-8-sig").rstrip("\r\n")
    row = next(csv.reader([decoded], strict=True))
    if not row or len(row) > MAX_COLUMNS or any(not f.strip() for f in row):
        raise ValueError("Invalid/empty/overwide CSV header")
    return row


def inspect_headers(archive_path, step36_path=PREFLIGHT):
    """Return metadata only; no clinical member body or patient IDs."""
    src = Path(archive_path).expanduser().resolve(strict=True)
    if not src.is_file() or not zipfile.is_zipfile(src):
        raise ValueError("Source is not a local ZIP")
    prior_bytes = owner_path(Path(step36_path)).read_bytes()
    prior = json.loads(prior_bytes)
    if (prior.get("stage") != "STEP36_RESEARCH_METADATA_PREFLIGHT"
            or prior.get("clinical_rows_read") != 0
            or prior.get("full_clinical_tables_scanned") is not False
            or prior.get("schema_supports_attempted_encounter_linkage") is not True):
        raise ValueError("Valid Step36 metadata-only preflight is required")
    with zipfile.ZipFile(src, "r") as archive:
        csv_infos = [info for info in archive.infolist()
                     if not info.is_dir() and info.filename.lower().endswith(".csv")]
        if not csv_infos or len(csv_infos) > MAX_MEMBERS:
            raise ValueError("ZIP CSV table count outside bounded metadata inventory limits")
        names = [clean_basename(info.filename) for info in csv_infos]
        duplicates = [name for name, count in Counter(names).items() if count > 1]
        if duplicates:
            raise ValueError("Duplicate CSV basename in ZIP; cannot identify table safely")
        by_name = dict(zip(names, csv_infos))
        preflight_files = prior.get("files", {})
        for name in CORE:
            info = by_name.get(name)
            expected = preflight_files.get(name, {})
            if (info is None or expected.get("present") is not True
                    or expected.get("uncompressed_bytes") != info.file_size):
                raise ValueError("ZIP does not match Step36 core table size signature")
        matches = []
        table_counts = {}
        for name, info in sorted(by_name.items()):
            fields = header_from_member(archive, info)
            if name in CORE:
                expected_fields = preflight_files.get(name, {}).get("headers")
                if fields != expected_fields:
                    raise ValueError("ZIP core header differs from Step36 saved metadata")
            strong_or_weak = []
            for field in fields:
                hint = field_hint(field)
                if hint:
                    # Only plausible column NAMES, never sample VALUES.
                    strong_or_weak.append({
                        "column_name": field, "hint_NOT_VALIDATED": hint
                    })
            if strong_or_weak:
                matches.append({"table_basename": name, "columns": strong_or_weak})
            table_counts[name] = len(fields)
        return {
            "stage": "STEP51_ALL_CSV_HEADER_ONLY_LINKAGE_SEARCH",
            "source_step36_sha256": hashlib.sha256(prior_bytes).hexdigest(),
            "zip_core_metadata_signature_reconciled": True,
            "csv_headers_examined": len(csv_infos),
            "table_header_column_counts": table_counts,
            "tables_with_candidate_identifier_field_names": matches,
            "clinical_rows_read": 0,
            "zip_member_bodies_scanned": False,
            "file_values_read": False,
            "site_identity_verified": False,
            "episode_linkage_verified": False,
            "source_id_is_verified_hco_key": False,
            "full_source_scan_authorized": False,
            "interpretation": (
                "Column names are hints ONLY. Check site/key semantics with the "
                "data steward. Absence of candidate field names is a structural "
                "finding, NOT proof that date-only ED/IP linkage is clinically valid."
            ),
        }


def save_private(report, destination=OUTPUT):
    path = owner_path(Path(destination))
    if path != owner_path(OUTPUT):
        raise ValueError("Step51 output must use the fixed private report filename")
    base = owner_path(PRIVATE)
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    if base.stat().st_mode & 0o077:
        raise PermissionError("Private site linkage review directory must be mode 0700")
    if path.exists():
        raise FileExistsError("Step51 private report exists; will not overwrite")
    fd, temp = tempfile.mkstemp(prefix=".step51_", dir=str(base))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
            f.write("\n")
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.link(temp, path)  # atomic create; never overwrite.
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, type=Path,
                        help="Existing private Research Network ZIP; read only")
    args = parser.parse_args()
    report = inspect_headers(args.zip)
    path = save_private(report)
    print("STEP51 HEADER ONLY: ZIP metadata + one header line per CSV.")
    print("CSV headers examined:", report["csv_headers_examined"])
    print("Tables with candidate column-name hints:",
          len(report["tables_with_candidate_identifier_field_names"]))
    for item in report["tables_with_candidate_identifier_field_names"]:
        print(" ", item["table_basename"] + ":",
              ", ".join(x["column_name"] for x in item["columns"]))
    print("Private report:", path)
    print("Clinical rows read: 0. Source id/HCO mapping NOT validated.")
    print("Full clinical-data scan remains BLOCKED.")


if __name__ == "__main__":
    main()
