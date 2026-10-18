#!/usr/bin/env python3
"""Stage-by-stage local Research Network full-source AGGREGATE technical QA.

Reads clinical input rows ONLY if invoked explicitly on the authorized user's
workstation. No patient or encounter identifiers are retained, logged, or
written to reports. Output is never suitable for public sharing as-is.
This is not a cohort reconstruction, HCO linkage assessment, or estimate of
actual imaging completion. Step45 remains disabled.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import stat
import tempfile
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "results" / "phase1" / "step36_research_metadata_preflight.json"
PRIVATE = ROOT / "results" / "phase1" / "full_reconstruction_private" / "source_wide_qa"
ACK = "I_CONFIRM_EXISTING_PROTOCOL_PERMITS_LOCAL_FULL_SOURCE_AGGREGATE_QA"
FIELDS = {
    "encounter": ("patient_id", "encounter_id", "type", "start_date", "end_date"),
    "procedure": ("patient_id", "encounter_id", "date", "code_system", "code"),
    "diagnosis": ("patient_id", "encounter_id", "date", "code_system", "code", "principal_diagnosis_indicator"),
}
SYSTEMS = frozenset({"CPT", "SNOMED", "HCPCS", "ICD-10-PCS", "ICD-9-CM", "ICD-10-CM"})
CPT14 = frozenset({"70450", "70460", "70470", "70496", "70498", "70544",
                   "70545", "70546", "70547", "70548", "70549", "70551",
                   "70552", "70553"})
CTP = frozenset({"0042T", "70472", "70473"})


def year_bucket(text, current_year=None):
    """Bucket dates without publishing exact dates or unbounded categories."""
    if current_year is None:
        current_year = date.today().year
    if not isinstance(text, str) or not text.strip():
        return "MISSING"
    val = text.strip()
    try:
        # TriNetX export uses unseparated calendar dates (YYYYMMDD).
        # Confirm year-month-day semantics; do not infer from eight digits alone.
        if len(val) == 8 and val.isascii() and val.isdigit():
            day = date(int(val[:4]), int(val[4:6]), int(val[6:8]))
        elif len(val) >= 10 and val[4] == "-" and val[7] == "-":
            day = date.fromisoformat(val[:10])
        else:
            return "INVALID"
    except ValueError:
        return "INVALID"
    if day.year < 2016:
        return "BEFORE_2016"
    if day.year > current_year:
        return "AFTER_CURRENT_YEAR"
    return str(day.year)


def _system(value):
    code = (value or "").strip().upper()
    return code if code in SYSTEMS else "OTHER_OR_EMPTY"


def _type(value):
    label = (value or "").strip().upper()
    return label if label in ("IMP", "EMER") else "OTHER_OR_EMPTY"


def _principal(value):
    label = (value or "").strip().upper()
    return "P" if label == "P" else "OTHER_OR_EMPTY"


def _scan_member(archive, member, stage, current_year=None):
    """One whole member; O(1) bounded counters in configured calendar window."""
    expected = FIELDS[stage]
    missing = Counter()
    counts_by_year = Counter()
    system_by_year = Counter()
    type_by_year = Counter()
    principal_by_year = Counter()
    imaging_by_year = Counter()
    rows = 0
    with archive.open(member, "r") as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="", errors="strict") as text:
        reader = csv.DictReader(text)
        fields = reader.fieldnames or []
        if not fields or len(fields) != len(set(fields)) or len(fields) > 150 or not set(expected).issubset(fields):
            raise ValueError("Source member has incompatible CSV header")
        for record in reader:
            if None in record or any(x is None for x in record.values()):
                raise ValueError("Malformed CSV record; no details emitted")
            rows += 1
            for key in expected:
                if not str(record.get(key) or "").strip():
                    missing[key] += 1
            d = record.get("start_date") if stage == "encounter" else record.get("date")
            bucket = year_bucket(d, current_year=current_year)
            counts_by_year[bucket] += 1
            if stage == "encounter":
                type_by_year[(bucket, _type(record.get("type")))] += 1
            else:
                system = _system(record.get("code_system"))
                system_by_year[(bucket, system)] += 1
                if stage == "diagnosis":
                    principal_by_year[(bucket, _principal(record.get("principal_diagnosis_indicator")))] += 1
                elif system == "CPT":
                    code = str(record.get("code") or "").strip()
                    if code in CPT14:
                        imaging_by_year[(bucket, "CPT14_CORE_CODE_ROWS")] += 1
                    elif code == "70471":
                        imaging_by_year[(bucket, "CTA_HEAD_NECK_70471_CANDIDATE")] += 1
                    elif code in CTP:
                        imaging_by_year[(bucket, "CT_PERFUSION_SEPARATE")] += 1
    def flatten(counter):
        return {"|".join(k): v for k, v in sorted(counter.items())}
    result = {
        "rows_scanned": rows,
        "missing_required_values": dict(sorted(missing.items())),
        "rows_by_year_bucket_NOT_COVERAGE_VERIFIED": dict(sorted(counts_by_year.items())),
        "code_system_by_year_bucket_NOT_PERFORMED_PROCEDURES": flatten(system_by_year),
        "encounter_type_by_year_bucket_NOT_INPATIENT_ADMISSIONS": flatten(type_by_year),
        "principal_indicator_by_year_bucket_NOT_VALIDATED": flatten(principal_by_year),
        "imaging_code_rows_by_year_NOT_SCANS_OR_PATIENTS": flatten(imaging_by_year),
        "patient_identifiers_emitted": False,
        "encounter_identifiers_emitted": False,
    }
    assert sum(counts_by_year.values()) == rows
    return result


def inspect(archive_path, stage, preflight_path=PREFLIGHT, current_year=None):
    """Read one source member only; never return patient/encounter IDs."""
    if stage not in FIELDS:
        raise ValueError("Stage must be encounter, diagnosis or procedure")
    prior = json.loads(Path(preflight_path).read_text(encoding="utf-8"))
    if (prior.get("stage") != "STEP36_RESEARCH_METADATA_PREFLIGHT" or
            prior.get("clinical_rows_read") != 0 or
            prior.get("full_clinical_tables_scanned") is not False):
        raise ValueError("Step36 metadata-only preflight required")
    name = stage + ".csv"
    files = prior.get("files", {})
    record = files.get(name, {})
    with zipfile.ZipFile(archive_path, "r") as archive:
        matches = [m for m in archive.infolist() if not m.is_dir() and
                   m.filename.replace("\\", "/").rsplit("/", 1)[-1].lower() == name]
        if len(matches) != 1:
            raise ValueError("Expected exactly one target CSV member")
        member = matches[0]
        if (record.get("present") is not True or
                member.file_size != record.get("uncompressed_bytes") or
                not set(FIELDS[stage]).issubset(record.get("headers", []))):
            raise ValueError("Source member size/header differs from Step36 preflight")
        with archive.open(member, "r") as stream:
            header = stream.readline(128*1024)
        if not header.endswith(b"\n") or len(header) >= 128*1024:
            raise ValueError("Invalid CSV header length")
        expected = next(csv.reader([header.decode("utf-8-sig").rstrip("\r\n")]))
        if expected != record["headers"]:
            raise ValueError("Source member header changed from Step36 preflight")
        values = _scan_member(archive, member, stage, current_year)
        # Do not write a report when the complete member did not reconcile.
        manifest = prior.get("relevant_manifest_counts", {}).get(name, {})
        expected_rows = manifest.get("row_count")
        if expected_rows is not None and expected_rows != values["rows_scanned"]:
            raise ValueError("Whole-member row count differs from Step36 manifest")
    return {
        "stage": "STEP59_FULL_SOURCE_AGGREGATE_QA_LOCAL_ONLY",
        "date_parser_version": "YYYYMMDD_OR_ISO8601_VALIDATED_V2",
        "table": name,
        "source_clinical_table_scanned_completely": True,
        "full_cohort_reconstruction_performed": False,
        "HCO_linkage_verified": False,
        "imaging_completion_verified": False,
        "final_study_end_year_approved": False,
        "approved_research_use_is_user_attested_NOT_VERIFIED_BY_CODE": True,
        "sharing_requires_disclosure_review": True,
        "result": values,
    }


def write_private(report, output, base=PRIVATE):
    folder = Path(base).resolve()
    location = Path(output).resolve()
    if location.parent != folder:
        raise ValueError("Report must stay in dedicated ignored private QA directory")
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.stat().st_mode & 0o077:
        raise PermissionError("Private QA directory must have mode 0700")
    if location.exists():
        raise FileExistsError("Stage report exists; overwrite disabled")
    fd, tmp = tempfile.mkstemp(prefix=".step59_", dir=str(folder))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.link(tmp, location)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return location



def probe_dates(archive_path, stage, max_rows=1000):
    """Small local format verification, never prints exact dates or raw rows."""
    if stage not in FIELDS or not (1 <= max_rows <= 1000):
        raise ValueError("Invalid probe stage or bounded row cap")
    member_name = stage + ".csv"
    summary = Counter()
    with zipfile.ZipFile(archive_path, "r") as archive:
        matches = [m for m in archive.infolist() if not m.is_dir()
                   and m.filename.replace("\\", "/").rsplit("/", 1)[-1].lower() == member_name]
        if len(matches) != 1:
            raise ValueError("Probe expected one source member")
        with archive.open(matches[0]) as raw, io.TextIOWrapper(
                raw, encoding="utf-8-sig", newline="", errors="strict") as text:
            reader = csv.DictReader(text)
            field = "start_date" if stage == "encounter" else "date"
            if field not in (reader.fieldnames or []):
                raise ValueError("Probe date column missing")
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                bucket = year_bucket(row.get(field))
                if bucket in ("INVALID", "MISSING", "BEFORE_2016", "AFTER_CURRENT_YEAR"):
                    summary[bucket] += 1
                else:
                    summary["PARSED_CALENDAR_DATE"] += 1
    return {name: summary[name] for name in (
        "PARSED_CALENDAR_DATE", "INVALID", "MISSING", "BEFORE_2016", "AFTER_CURRENT_YEAR")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--stage", choices=tuple(FIELDS), required=True)
    parser.add_argument("--acknowledge", required=True)
    parser.add_argument("--datefix-v2", action="store_true",
                        help="Write distinct v2 corrected-date private report")
    parser.add_argument("--probe-dates", action="store_true",
                        help="Validate at most 1000 date values without full scan or report")
    args = parser.parse_args(argv)
    if args.acknowledge != ACK:
        parser.error("Existing-protocol approval attestation required for source-wide scan")
    if args.probe_dates:
        tally = probe_dates(args.zip, args.stage)
        print("Bounded date-parser validation only; no source data values printed.")
        print("Rows by parsing status:", tally)
        return
    if not args.datefix_v2:
        parser.error("The YYYYMMDD date correction requires --datefix-v2; old reports remain untouched")
    outfile = PRIVATE / ("step59_" + args.stage + "_DATEFIX_V2_LOCAL_ONLY.json")
    if outfile.exists():
        parser.error("Corrected report exists; refusing repeat full-source pass")
    result = inspect(args.zip, args.stage)
    saved = write_private(result, outfile)
    print("Step59 completed full-source aggregate QA for one core table.")
    print("Private report:", saved)
    print("No clinical values printed. Do NOT upload the private report.")
    print("Not a validated study-year determination or cohort reconstruction.")


if __name__ == "__main__":
    main()
