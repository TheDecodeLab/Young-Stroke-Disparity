#!/usr/bin/env python3
"""Step58: explicitly authorized LOCAL bounded-prefix clinical-data QA.

Reads at most --max-rows-per-table source clinical rows from each of four
core CSV members, ONLY on the owner's workstation, never through GitHub.
Defaults do NOTHING without explicit local opt-in and a Step36 signature.
Does NOT assess source-wide representativeness, year coverage, code-system
prevalence or completed imaging. Does NOT unlock the obsolete Step45 scan.
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
from itertools import islice
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase1" / "full_reconstruction_private" / "step58_bounded_prefix_qa_LOCAL_ONLY.json"
PREFLIGHT = ROOT / "results" / "phase1" / "step36_research_metadata_preflight.json"
ACCEPT = "I_CONFIRM_APPROVED_LOCAL_BOUNDED_CLINICAL_QA"
MEMBERS = {
    "patient.csv": ("patient_id", "sex", "race", "ethnicity", "year_of_birth"),
    "encounter.csv": ("patient_id", "encounter_id", "start_date", "end_date", "type"),
    "diagnosis.csv": ("patient_id", "encounter_id", "code_system", "code", "date", "principal_diagnosis_indicator"),
    "procedure.csv": ("patient_id", "encounter_id", "code_system", "code", "date"),
}
CHECK_MISSING = {
    "patient.csv": ("patient_id", "year_of_birth", "sex", "race", "ethnicity"),
    "encounter.csv": ("patient_id", "encounter_id", "start_date", "end_date", "type"),
    "diagnosis.csv": ("patient_id", "encounter_id", "date", "code_system", "code", "principal_diagnosis_indicator"),
    "procedure.csv": ("patient_id", "encounter_id", "date", "code_system", "code"),
}
DATE_FIELDS = {
    "encounter.csv": ("start_date", "end_date"),
    "diagnosis.csv": ("date",),
    "procedure.csv": ("date",),
}
CORE_CPT14 = frozenset(("70450", "70460", "70470", "70496", "70498",
                        "70544", "70545", "70546", "70547", "70548", "70549",
                        "70551", "70552", "70553"))
SYSTEMS = {"CPT", "SNOMED", "ICD-10-PCS", "ICD-9-CM", "HCPCS"}


def _private_output(path):
    base=(ROOT/"results"/"phase1"/"full_reconstruction_private").resolve()
    p=Path(path).expanduser().resolve()
    if not (p == base or base in p.parents):
        raise ValueError("Output must be inside ignored private results/phase1 directory")
    return p


def _year(value):
    """Only interpret unambiguous leading ISO date, never guess formats."""
    val=(value or "").strip()
    if len(val)<10:
        return None
    try:
        return date.fromisoformat(val[:10]).year
    except ValueError:
        return None


def _sample_table(source, zip_member, table_name, required, max_rows):
    """Returns aggregate-only counters; never preserves clinical input rows."""
    if table_name not in MEMBERS:
        raise ValueError("Unknown expected core table")
    missing=Counter()
    bad_date=Counter()
    seen_years=set()
    systems=Counter()
    visit_types=Counter()
    principal=Counter()
    core_cpt14=0
    rows=0
    # TextIOWrapper and csv.DictReader bounded read; no extraction to disk.
    with source.open(zip_member, "r") as raw:
        with io.TextIOWrapper(raw, encoding="utf-8-sig", errors="strict", newline="") as txt:
            reader=csv.DictReader(txt)
            columns=reader.fieldnames or []
            if len(columns)!=len(set(columns)):
                raise ValueError("Duplicate CSV header names in "+table_name)
            if len(columns)>150 or len(columns)==0:
                raise ValueError("Core table header unexpectedly large or empty")
            if not set(required).issubset(columns):
                raise ValueError("Core table missing expected columns in "+table_name)
            for row in islice(reader, max_rows):
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("Malformed CSV row in "+table_name)
                rows+=1
                for key in CHECK_MISSING[table_name]:
                    if not (row.get(key) or "").strip():
                        missing[key]+=1
                for key in DATE_FIELDS.get(table_name, ()):
                    val=(row.get(key) or "").strip()
                    if val:
                        y=_year(val)
                        if y is None:
                            bad_date[key]+=1
                        elif key in ("date", "start_date"):
                            seen_years.add(y)
                if table_name in ("procedure.csv","diagnosis.csv"):
                    label=(row.get("code_system") or "").strip().upper()
                    systems[label if label in SYSTEMS else "OTHER_OR_EMPTY"]+=1
                if table_name=="encounter.csv":
                    label=(row.get("type") or "").strip().upper()
                    visit_types[label if label in ("IMP","EMER") else "OTHER_OR_EMPTY"]+=1
                if table_name=="diagnosis.csv":
                    label=(row.get("principal_diagnosis_indicator") or "").strip().upper()
                    principal["P" if label=="P" else "OTHER_OR_EMPTY"]+=1
                if table_name=="procedure.csv" and (
                        (row.get("code_system") or "").strip().upper()=="CPT"
                        and (row.get("code") or "").strip() in CORE_CPT14):
                    core_cpt14+=1
    return {
        "rows_in_prefix": rows,
        "limit_rows_per_table": max_rows,
        "truncated_by_design": rows>=max_rows,
        "missing_field_counts_in_prefix": dict(sorted(missing.items())),
        "unparseable_nonblank_date_counts_in_prefix": dict(sorted(bad_date.items())),
        "observed_years_in_prefix_NOT_COVERAGE": sorted(seen_years),
        "code_system_counts_in_prefix_NOT_PREVALENCE": dict(sorted(systems.items())),
        "encounter_type_counts_in_prefix_NOT_FULL_SOURCE": dict(sorted(visit_types.items())),
        "principal_P_counts_in_prefix_NOT_VALIDATION": dict(sorted(principal.items())),
        "CPT14_code_rows_in_prefix_NOT_CAPTURE_RATE": core_cpt14,
        "source_identifiers_emitted": False,
        "raw_clinical_rows_emitted": False,
    }


def inspect(archive_path, preflight_path=PREFLIGHT, max_rows=500):
    if isinstance(max_rows,bool) or not isinstance(max_rows,int) or not 1<=max_rows<=1000:
        raise ValueError("Bounded pilot requires 1-1000 rows per table")
    preflight=json.loads(Path(preflight_path).read_bytes())
    if (preflight.get("stage")!="STEP36_RESEARCH_METADATA_PREFLIGHT"
        or preflight.get("clinical_rows_read")!=0
        or preflight.get("full_clinical_tables_scanned") is not False):
        raise ValueError("Trusted metadata-only Step36 preflight must precede pilot")
    files=preflight.get("files",{})
    with zipfile.ZipFile(archive_path, "r") as archive:
        mapping={}
        for info in archive.infolist():
            if info.is_dir():
                continue
            name=info.filename.replace("\\","/").rsplit("/",1)[-1].lower()
            if name in MEMBERS:
                if name in mapping:
                    raise ValueError("Duplicate core-table basename in source ZIP")
                mapping[name]=info
        if set(mapping)!=set(MEMBERS):
            raise ValueError("Expected four core Research Network tables")
        for name in MEMBERS:
            previous=files.get(name,{})
            if (previous.get("present") is not True or
                previous.get("uncompressed_bytes")!=mapping[name].file_size or
                not set(MEMBERS[name]).issubset(previous.get("headers",[]))):
                raise ValueError("Source ZIP does not match prior Step36 metadata signature")
        tables={}
        for name in MEMBERS:
            # Check the actual header matches the Step36 metadata, not just
            # sizes. Clinical row values never leave _sample_table().
            with archive.open(mapping[name],"r") as member:
                first=member.readline(128*1024)
            if not first.endswith(b"\n"):
                raise ValueError("Incomplete CSV header")
            observed=next(csv.reader([first.decode("utf-8-sig").rstrip("\r\n")]))
            if observed!=files[name]["headers"]:
                raise ValueError("Changed table header since Step36")
            tables[name]=_sample_table(archive,mapping[name],name,MEMBERS[name],max_rows)
    return {
        "stage":"STEP58_BOUNDED_CLINICAL_PREFIX_TECHNICAL_PILOT_LOCAL_ONLY",
        "source":"user_workstation_under_user_attested_existing_protocol",
        "rows_upper_bound_per_member":max_rows,
        "clinical_rows_inspected_limited_prefix_only":True,
        "full_clinical_table_scanned":False,
        "random_sample":False,
        "network_wide_estimates_permitted":False,
        "research_network_end_year_confirmed":False,
        "CPT14_source_completeness_confirmed":False,
        "HCO_and_ED_IP_linkage_validated":False,
        "clinical_scan_authorized_by_this_tool":False,
        "old_step45_scan_unblocked":False,
        "raw_patient_or_encounter_identifiers_in_output":False,
        "sharing_allowed_without_disclosure_review":False,
        "tables":tables,
    }


def save_private(report, output=OUT):
    path=_private_output(output)
    if path.exists():
        raise FileExistsError("Step58 private pilot report already exists; no overwrite")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.stat().st_mode & 0o077:
        raise PermissionError("Private output directory must have 0700 permissions")
    fd,tmp=tempfile.mkstemp(prefix=".step58_",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump(report,out,sort_keys=True,indent=2)
            out.write("\n")
        os.chmod(tmp, stat.S_IRUSR|stat.S_IWUSR)
        os.link(tmp,path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip",required=True,type=Path)
    parser.add_argument("--max-rows-per-table",type=int,default=500)
    parser.add_argument("--acknowledge",required=True,help="Explicit approved-local-use attestation")
    args=parser.parse_args()
    if args.acknowledge!=ACCEPT:
        parser.error("Explicit local data-use attestation does not match")
    if _private_output(OUT).exists():
        parser.error("Private pilot output already exists; refusing to rescan")
    result=inspect(args.zip,max_rows=args.max_rows_per_table)
    saved=save_private(result)
    print("Step58 private, bounded-prefix technical pilot completed.")
    print("Source clinical rows remained on approved workstation. No row-level values printed.")
    print("Private report:",saved)
    print("NOT a full-source year/code-system coverage study. Do not upload private report.")
    print("Old Step45 full clinical scan remains disabled.")


if __name__=="__main__":
    main()
