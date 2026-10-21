#!/usr/bin/env python3
"""Step55: apply literature-backed CPT meanings to PREEXISTING private Step46
reference terminology inventory only. No source ZIP/clinical row access.

Produces evidence-coded dispositions and a 14-CPT *candidate*, not a signed
or approved performed-imaging clinical codebook. Leaves Step46/47 worksheets,
local approval files and imaging codebook completely unchanged.
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
from collections import Counter
from pathlib import Path

try:
    from .step46_47_imaging_review_bundle import (
        DEST, INVENTORY, STATUS, REVIEW_COLS, within, private_folder,
    )
    from .step54_literature_imaging_registry import BASE_CPT, classify_imaging_code, research_network_period_policy
except ImportError:
    from step46_47_imaging_review_bundle import (
        DEST, INVENTORY, STATUS, REVIEW_COLS, within, private_folder,
    )
    from step54_literature_imaging_registry import BASE_CPT, classify_imaging_code, research_network_period_policy

OUTDIR = DEST / "literature_adjudication"
DISPOSITIONS = "all_reference_literature_dispositions_LOCAL_ONLY.csv"
CORE_MATCHES = "CPT14_core_reference_matches_CANDIDATE_NOT_APPROVED_LOCAL_ONLY.csv"
SUMMARY = "literature_code_review_summary_LOCAL_ONLY.json"
COLS = (
    "review_id", "code_system", "code", "literature_status",
    "literature_category", "secondary_category", "external_meaning",
    "external_evidence_url", "reference_term_conflict_flag",
    "procedure_record_performed_NOT_VERIFIED", "local_code_mapping_NOT_VERIFIED",
)
CORE_COLS = ("code_system", "code", "category", "evidence_url",
             "source_code_meaning_NOT_PERFORMED_EVENT_VERIFIED")
REQUIRED = ("review_id", "code_system", "code", "reference_description",
            "reference_path", "automated_candidate_NOT_APPROVED")


def term_conflicts(system, code, description, refpath):
    """Conservative explicit contradiction screen; absence is NOT validation."""
    if system != "CPT" or code not in BASE_CPT:
        return False
    text = (description + " " + refpath).upper()
    # Require a clear different body region/modality claim, not missing words.
    if re.search(r"\b(PELVIS|ABDOMEN|ABDOMINAL|CHEST|THORAX|KNEE|HIP|SPINE|LUMBAR)\b", text):
        return True
    wanted = BASE_CPT[code][0]
    if wanted.startswith("M"):
        return bool(re.search(r"\b(CT\s+ANGIOGRAPHY|COMPUTED\s+TOMOGRAPHY|ULTRASOUND)\b", text))
    return bool(re.search(r"\b(MRI|MRA|MAGNETIC\s+RESONANCE)\b", text))


def review_reference_rows(rows):
    decisions = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("Review input must be dictionaries")
        if not all(key in row for key in REQUIRED):
            raise ValueError("Private reference worksheet missing provenance columns")
        refid = (row["review_id"] or "").strip()
        system = (row["code_system"] or "").strip().upper()
        code = (row["code"] or "").strip().upper()
        if not re.fullmatch(r"[0-9a-f]{64}", refid):
            raise ValueError("Invalid Step46 hashed identity; do not guess provenance")
        if refid in seen:
            raise ValueError("Duplicate Step46 reference review_id")
        seen.add(refid)
        candidate = classify_imaging_code(system, code)
        contradiction = term_conflicts(
            system, code, row["reference_description"] or "",
            row["reference_path"] or "",
        )
        if contradiction:
            candidate["status"] = "hold_CPT_external_vs_local_terminology_CONFLICT"
            candidate["category"] = None
        decisions.append({
            "review_id": refid, "code_system": system, "code": code,
            "literature_status": candidate["status"],
            "literature_category": candidate["category"] or "",
            "secondary_category": candidate["secondary_category"] or "",
            "external_meaning": candidate["meaning"],
            "external_evidence_url": candidate["source_url"] or "",
            "reference_term_conflict_flag": "yes" if contradiction else "no",
            "procedure_record_performed_NOT_VERIFIED": "NOT_VERIFIED",
            "local_code_mapping_NOT_VERIFIED": "NOT_VERIFIED",
        })
    return decisions


def summarized(decisions, source_meta):
    counts = dict(sorted(Counter(row["literature_status"] for row in decisions).items()))
    code_set = {row["code"] for row in decisions
                if row["code_system"] == "CPT" and
                row["literature_status"] == "core_exact_CPT_modality_candidate"}
    core = [{
        "code_system": "CPT", "code": code,
        "category": BASE_CPT[code][0],
        "evidence_url": classify_imaging_code("CPT", code)["source_url"],
        "source_code_meaning_NOT_PERFORMED_EVENT_VERIFIED": "NOT_PERFORMED_VERIFIED",
    } for code in sorted(code_set)]
    return core, {
        "stage": "STEP55_LITERATURE_BASED_TERMINOLOGY_ADJUDICATION_ONLY",
        "source_step46_status_sha256": source_meta["status_sha256"],
        "source_step46_inventory_sha256": source_meta["inventory_sha256"],
        "reference_rows_examined": len(decisions),
        "literature_status_counts": counts,
        "unique_CPT14_anchors_located": len(code_set),
        "expected_core_CPT_code_count": len(BASE_CPT),
        "CPT14_missing_from_local_reference_inventory": sorted(
            set(BASE_CPT) - code_set
        ),
        "research_network_period_policy": research_network_period_policy()["research_network"],
        "diamond_study_period": research_network_period_policy()["diamond"],
        "clinical_event_rows_read": 0,
        "original_research_ZIP_opened": False,
        "reference_inventory_only": True,
        "CPT14_external_code_meanings_researched": True,
        "unmapped_nonCPT_code_meanings_independently_validated": False,
        "performed_procedure_meaning_approved": False,
        "codebook_signed_off": False,
        "source_system_mapping_confirmed": False,
        "data_use_approval_changed": False,
        "full_clinical_scan_performed": False,
    }


def _csvbytes(rows, fields):
    sio = io.StringIO(newline="")
    writer = csv.DictWriter(sio, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        safe = {k: str(row.get(k, "") or "") for k in fields}
        for k,v in safe.items():
            if v.lstrip().startswith(("=", "+", "-", "@")):
                safe[k] = "'" + v
        writer.writerow(safe)
    return sio.getvalue().encode("utf-8")


def _atomic_new(path, blob):
    """Creates a private file with no overwrite and restrictive permissions."""
    path = within(path)
    fd, tmp = tempfile.mkstemp(prefix=".step55_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(blob)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.link(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def prepare(source=DEST, destination=OUTDIR):
    folder = within(source)
    out = within(destination)
    expected = [out / name for name in (DISPOSITIONS, CORE_MATCHES, SUMMARY)]
    if any(path.exists() for path in expected):
        raise FileExistsError("Step55 literature review outputs already exist; refusing overwrite")
    with (folder / STATUS).open(encoding="utf-8") as f:
        status = json.load(f)
    if (status.get("stage") != "STEP46_PRIVATE_IMAGING_REVIEW_PREPARED"
            or status.get("clinical_event_rows_read") != 0
            or status.get("codebook_clinically_validated") is not False):
        raise ValueError("Existing Step46 inventory status not a safe reference-only artifact")
    contents = (folder / INVENTORY).read_bytes()
    with io.StringIO(contents.decode("utf-8-sig"), newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != REVIEW_COLS:
            raise ValueError("Step46 full reference inventory schema changed")
        reference_rows = list(reader)
    if len(reference_rows) != status.get("full_reference_candidate_entries_preserved"):
        raise ValueError("Private Step46 inventory row count differs from status")
    meta = {
        "status_sha256": hashlib.sha256((folder / STATUS).read_bytes()).hexdigest(),
        "inventory_sha256": hashlib.sha256(contents).hexdigest(),
    }
    decisions = review_reference_rows(reference_rows)
    core, summary = summarized(decisions, meta)
    private_folder(out)
    _atomic_new(out / DISPOSITIONS, _csvbytes(decisions, COLS))
    _atomic_new(out / CORE_MATCHES, _csvbytes(core, CORE_COLS))
    _atomic_new(out / SUMMARY, (json.dumps(summary, indent=2, sort_keys=True)+"\n").encode())
    print("STEP55 literature review of existing private reference terminology completed.")
    print("Reference terminology entries classified:", len(decisions))
    print("Distinct core CPT codes present:", len(core), "of", len(BASE_CPT))
    print("Adjudication status counts:", summary["literature_status_counts"])
    print("Private output directory:", out)
    print("No clinical rows read. CPT meaning evidence != performed imaging validation.")
    print("Research Network period is NOT restricted to Diamond 2018-2019.")
    print("Step47 signoff and full clinical-source scan remain unchanged and disabled.")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["prepare"])
    args = ap.parse_args()
    prepare()


if __name__ == "__main__":
    main()
