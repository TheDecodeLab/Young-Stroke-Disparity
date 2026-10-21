#!/usr/bin/env python3
"""Step56: reference-only coverage triage after Step55 literature classification.

No source ZIP or patient/encounter/procedure rows. Reads existing PRIVATE
Step46 terminology review and Step55 literature dispositions, matches
provenance and writes one owner-only review package. Never auto-approves
non-CPT mappings or clinical scan access.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import stat
import tempfile
from collections import Counter
from pathlib import Path

try:
    from .step46_47_imaging_review_bundle import (
        DEST, INVENTORY, STATUS, REVIEW_COLS, within, private_folder,
    )
    from .step55_private_literature_codebook_review import (
        OUTDIR, DISPOSITIONS, SUMMARY, COLS,
    )
except ImportError:
    from step46_47_imaging_review_bundle import (
        DEST, INVENTORY, STATUS, REVIEW_COLS, within, private_folder,
    )
    from step55_private_literature_codebook_review import (
        OUTDIR, DISPOSITIONS, SUMMARY, COLS,
    )

TRIAGE_DIR = OUTDIR / "coverage_triage"
REPORT = "step56_reference_system_coverage_LOCAL_ONLY.json"
CPT_QUEUE = "step56_deferred_CPT_reference_queue_LOCAL_ONLY.csv"
QUEUE_FIELDS = (
    "code_system", "code", "step46_review_id",
    "original_terminology_description_LOCAL_ONLY",
    "original_terminology_category_NOT_VALIDATED",
    "literature_status",
    "verified_external_coding_meaning_PENDING",
    "source_record_performed_semantics_PENDING",
)


def _parse_csv(blob: bytes, expected):
    with io.StringIO(blob.decode("utf-8-sig"), newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != tuple(expected):
            raise ValueError("Private reference CSV schema mismatch")
        records = list(reader)
    if any(None in row for row in records):
        raise ValueError("Private reference CSV malformed row")
    return records


def analyze(step46_rows, step55_rows, metadata):
    """Compare every Step55 disposition to its original Step46 identity."""
    if len(step46_rows) != metadata["reference_rows_examined"]:
        raise ValueError("Step46 reference count does not match Step55 status")
    reference = {}
    for row in step46_rows:
        key = row["review_id"]
        if not key or key in reference:
            raise ValueError("Duplicate or empty Step46 review_id")
        reference[key] = row
    joined = []
    seen = set()
    for row in step55_rows:
        key = row["review_id"]
        if key in seen or key not in reference:
            raise ValueError("Missing or duplicate Step55/Step46 reference key")
        seen.add(key)
        prior = reference[key]
        if (row["code_system"].strip().upper() != prior["code_system"].strip().upper()
                or row["code"].strip().upper() != prior["code"].strip().upper()):
            raise ValueError("Step55 disposition code differs from Step46 source")
        joined.append((prior, row))
    if seen != set(reference):
        raise ValueError("Step55 missing original reference candidates")
    statuses = Counter(row["literature_status"] for _,row in joined)
    if dict(statuses) != metadata["literature_status_counts"]:
        raise ValueError("Step55 saved literature status counts do not reconcile")
    systems = Counter(row["code_system"].strip().upper() for _,row in joined)
    system_status = Counter(
        (row["code_system"].strip().upper(),row["literature_status"])
        for _,row in joined
    )
    system_category = Counter(
        (row["code_system"].strip().upper(),
         prior["automated_candidate_NOT_APPROVED"].strip())
        for prior,row in joined
    )
    deferred_cpt = []
    for prior,row in joined:
        if (row["code_system"].strip().upper()=="CPT"
                and row["literature_status"]=="defer_CPT_not_in_literature_core"):
            deferred_cpt.append({
                "code_system": "CPT",
                "code": row["code"],
                "step46_review_id": row["review_id"],
                "original_terminology_description_LOCAL_ONLY":
                    prior["reference_description"],
                "original_terminology_category_NOT_VALIDATED":
                    prior["automated_candidate_NOT_APPROVED"],
                "literature_status": row["literature_status"],
                "verified_external_coding_meaning_PENDING": "PENDING",
                "source_record_performed_semantics_PENDING": "PENDING",
            })
    deferred_cpt.sort(key=lambda r:(r["code"],r["step46_review_id"]))
    return {
        "stage": "STEP56_REFERENCE_VOCABULARY_COVERAGE_TRIAGE_ONLY",
        "reference_entries_reconciled": len(joined),
        "reference_counts_by_code_system": dict(sorted(systems.items())),
        "code_system_by_literature_status_counts": [
            {"code_system": system, "status": status, "reference_entries": count}
            for (system,status),count in sorted(system_status.items())
        ],
        "code_system_by_automated_text_category_counts": [
            {"code_system": system,
             "lexical_candidate_NOT_CLINICALLY_VALIDATED": category,
             "reference_entries": count}
            for (system,category),count in sorted(system_category.items())
        ],
        "deferred_CPT_entries_for_targeted_external_review": len(deferred_cpt),
        "unmapped_code_systems_recorded_in_actual_procedure_events": "UNKNOWN",
        "reference_terminology_counts_are_NOT_procedure_use_frequencies": True,
        "research_network_study_period_end_verified": False,
        "patient_or_clinical_event_rows_read": 0,
        "Research_Network_ZIP_opened": False,
        "source_data_use_authorized_by_this_step": False,
        "clinical_codebook_approved": False,
        "full_clinical_scan_enabled": False,
        "review_policy": (
            "Research the deferred CPT codes against versioned external "
            "coding sources; map non-CPT exact concepts ONLY with independently "
            "supported code meanings and source-system semantics. No lexical "
            "candidate is automatically approved as completed imaging."
        ),
    }, deferred_cpt


def _csv_data(records):
    data=io.StringIO(newline="")
    writer=csv.DictWriter(data,fieldnames=QUEUE_FIELDS,lineterminator="\n")
    writer.writeheader()
    for row in records:
        safe={k:str(row.get(k,"") or "") for k in QUEUE_FIELDS}
        for k,value in safe.items():
            if value.lstrip().startswith(("=","+","-","@")):
                safe[k]="'"+value
        writer.writerow(safe)
    return data.getvalue().encode("utf-8")


def _write_new(path: Path, payload: bytes):
    path=within(path)
    fd,temp=tempfile.mkstemp(prefix=".step56_",dir=str(path.parent))
    try:
        with os.fdopen(fd,"wb") as handle:
            handle.write(payload)
        os.chmod(temp, stat.S_IRUSR|stat.S_IWUSR)
        os.link(temp,path)  # atomic create; never overwrite
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def prepare(source=DEST, step55=OUTDIR, output=TRIAGE_DIR):
    """Private-only reference report. No approval or scan interaction."""
    src,directory,dst=within(source),within(step55),within(output)
    filenames=(dst/REPORT,dst/CPT_QUEUE)
    if any(path.exists() for path in filenames):
        raise FileExistsError("Step56 report exists: refusing to overwrite local review")
    step46_status_bytes=(src/STATUS).read_bytes()
    step46_status=json.loads(step46_status_bytes)
    if (step46_status.get("stage")!="STEP46_PRIVATE_IMAGING_REVIEW_PREPARED"
            or step46_status.get("clinical_event_rows_read")!=0
            or step46_status.get("codebook_clinically_validated") is not False):
        raise ValueError("Step46 must be reference-only and not signed off")
    inventory=(src/INVENTORY).read_bytes()
    metadata=json.loads((directory/SUMMARY).read_bytes())
    if (metadata.get("stage")!="STEP55_LITERATURE_BASED_TERMINOLOGY_ADJUDICATION_ONLY"
            or metadata.get("clinical_event_rows_read")!=0
            or metadata.get("codebook_signed_off") is not False
            or metadata.get("full_clinical_scan_performed") is not False
            or metadata.get("source_step46_status_sha256")!=
                hashlib.sha256(step46_status_bytes).hexdigest()
            or metadata.get("source_step46_inventory_sha256")!=
                hashlib.sha256(inventory).hexdigest()):
        raise ValueError("Step55 lineage/signoff provenance invalid")
    step46_rows=_parse_csv(inventory,REVIEW_COLS)
    step55_rows=_parse_csv((directory/DISPOSITIONS).read_bytes(),COLS)
    summary,cpt_queue=analyze(step46_rows,step55_rows,metadata)
    if summary["reference_entries_reconciled"]!=step46_status.get(
            "full_reference_candidate_entries_preserved"):
        raise ValueError("Step46 count disagrees with reconciled terminology")
    private_folder(dst)
    _write_new(dst/REPORT,(json.dumps(summary,indent=2,sort_keys=True)+"\n").encode())
    _write_new(dst/CPT_QUEUE,_csv_data(cpt_queue))
    print("STEP56 reference vocabulary coverage triage completed.")
    print("Reference entries (not clinical procedures):",summary["reference_entries_reconciled"])
    print("Reference entries by code system:",summary["reference_counts_by_code_system"])
    print("Deferred CPT entries for targeted literature review:",
          summary["deferred_CPT_entries_for_targeted_external_review"])
    print("Private local summary:",dst/REPORT)
    print("Private local CPT review queue:",dst/CPT_QUEUE)
    print("No patient records read. Nothing clinically approved; full scan BLOCKED.")
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["prepare"])
    args=parser.parse_args()
    prepare()


if __name__=="__main__":
    main()
