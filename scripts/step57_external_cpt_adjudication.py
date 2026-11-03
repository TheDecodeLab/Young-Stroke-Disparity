#!/usr/bin/env python3
"""Step57: evidence adjudication of Step56's private deferred CPT queue.

Reference terminology ONLY. Does NOT open source ZIP, clinical tables,
approved codebook, or institution's permissions. Does NOT finalize codebook.
The eight externally documented CPT procedures are not target DIAGNOSTIC
MRI/CTA/MRA/CT exams. Other/invalid CPT-like strings remain unresolved.
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

try:
    from .step46_47_imaging_review_bundle import within, private_folder
    from .step56_reference_vocabulary_coverage_triage import (
        TRIAGE_DIR, CPT_QUEUE, REPORT, QUEUE_FIELDS,
    )
except ImportError:
    from step46_47_imaging_review_bundle import within, private_folder
    from step56_reference_vocabulary_coverage_triage import (
        TRIAGE_DIR, CPT_QUEUE, REPORT, QUEUE_FIELDS,
    )

OUT = TRIAGE_DIR / "external_evidence_adjudication"
DECISIONS = "step57_deferred_CPT_external_evidence_LOCAL_ONLY.csv"
SUMMARY = "step57_external_evidence_summary_LOCAL_ONLY.json"

# These codes and external source links are public CPT reference data.
# Not a claim that an actual Research Network imaging study was performed.
PUBLIC_EXCLUSIONS = {
    "0398T": (
        "MRI-guided focused ultrasound ablation for movement disorders",
        "https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=58323&ver=12",
        "2016-through-2024; replaced by 61715 effective 2025-01-01",
    ),
    "0865T": (
        "Quantitative brain MRI image analysis without diagnostic MRI in the same session",
        "https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=60245",
        "effective 2024-01-01; software analysis not diagnostic MRI acquisition",
    ),
    "0866T": (
        "Quantitative brain MRI image analysis with diagnostic MRI in the same session",
        "https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=60245",
        "effective 2024-01-01; adjunct analysis not stand-alone MRI acquisition",
    ),
    "61736": (
        "Intracranial laser interstitial thermal therapy, single trajectory",
        "https://www.aapc.com/codes/cpt-codes/61736",
        "service years require version validation; therapeutic surgery",
    ),
    "61737": (
        "Intracranial laser interstitial thermal therapy, multiple trajectories",
        "https://www.aapc.com/codes/cpt-codes/61737",
        "service years require version validation; therapeutic surgery",
    ),
    "61751": (
        "Stereotactic intracranial biopsy or excision with CT/MR guidance",
        "https://www.aapc.com/codes/cpt-codes/61751",
        "service years require version validation; surgery guided by imaging",
    ),
    "78814": (
        "Tumor PET/CT limited-area imaging, not diagnostic brain CT",
        "https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=54953&ver=68",
        "service years require version validation; nuclear medicine PET/CT",
    ),
    "78830": (
        "Radiopharmaceutical SPECT/CT localization, not diagnostic brain CT",
        "https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=54953&ver=68",
        "2024 vocabulary evidence; verify relevant historical code version",
    ),
}

# CPT Category I: five digits; II/III: four digits + F/T. This screens
# format; it never independently validates the code's existence or meaning.
CPT_SHAPE = re.compile(r"(?:[0-9]{5}|[0-9]{4}[FT])\Z")
OUTPUT_FIELDS = (
    "code_system", "code", "step46_review_id",
    "original_terminology_description_LOCAL_ONLY",
    "external_evidence_decision", "external_code_meaning",
    "public_evidence_url", "version_scope_note",
    "approved_for_core_diagnostic_imaging", "source_code_system_mapping_verified",
    "source_event_performed_status_verified",
)


def classify(code):
    """Known 8 external exclusions, nonstandard shape holds, other holds."""
    code = str(code or "").strip().upper()
    if code in PUBLIC_EXCLUSIONS:
        meaning, link, period = PUBLIC_EXCLUSIONS[code]
        return {
            "decision": "exclude_from_six_diagnostic_imaging_categories",
            "external_meaning": meaning, "evidence_url": link,
            "version_note": period,
            "source_system_mapping_verified": "NOT_VERIFIED",
        }
    if not CPT_SHAPE.fullmatch(code):
        return {
            "decision": "hold_nonstandard_CPT_shape_CHECK_ORIGINAL_CODE_SYSTEM",
            "external_meaning": "No standard five-character CPT code established",
            "evidence_url": "https://www.ama-assn.org/practice-management/cpt/cpt-code-set-basics-and-resources",
            "version_note": "Possible local/transformed identifier; no inferred code identity",
            "source_system_mapping_verified": "NOT_VERIFIED",
        }
    return {
        "decision": "defer_other_CPT_REQUIRES_EXACT_CODE_EVIDENCE",
        "external_meaning": "Not independently researched in versioned public code list",
        "evidence_url": "",
        "version_note": "Full CPT meaning and service year must be verified",
        "source_system_mapping_verified": "NOT_VERIFIED",
    }


def adjudicate(rows):
    """Use private existing queue; do not publish its identifiers."""
    records, seen = [], set()
    for item in rows:
        if not isinstance(item, dict):
            raise TypeError("Step56 queue must contain dictionaries")
        if not all(x in item for x in QUEUE_FIELDS):
            raise ValueError("Step56 queue missing required metadata columns")
        system = str(item["code_system"]).strip().upper()
        code = str(item["code"]).strip().upper()
        review_id = str(item["step46_review_id"]).strip().lower()
        if (system != "CPT" or
            item["literature_status"] != "defer_CPT_not_in_literature_core" or
            not re.fullmatch(r"[0-9a-f]{64}", review_id)):
            raise ValueError("Step56 queue provenance or code-system status invalid")
        key = (system, code, review_id)
        if key in seen:
            raise ValueError("Duplicate Step56 CPT queue identity")
        seen.add(key)
        info = classify(code)
        records.append({
            "code_system": system, "code": code, "step46_review_id": review_id,
            "original_terminology_description_LOCAL_ONLY":
                item["original_terminology_description_LOCAL_ONLY"],
            "external_evidence_decision": info["decision"],
            "external_code_meaning": info["external_meaning"],
            "public_evidence_url": info["evidence_url"],
            "version_scope_note": info["version_note"],
            "approved_for_core_diagnostic_imaging": "NO",
            "source_code_system_mapping_verified": info["source_system_mapping_verified"],
            "source_event_performed_status_verified": "NOT_VERIFIED",
        })
    return records


def _csv_read(blob):
    with io.StringIO(blob.decode("utf-8-sig"), newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != QUEUE_FIELDS:
            raise ValueError("Step56 deferred CPT queue schema mismatch")
        rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError("Invalid Step56 CSV rows")
    return rows


def _csv_encode(rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        safe = {}
        for k in OUTPUT_FIELDS:
            v = str(r.get(k, "") or "")
            safe[k] = "'" + v if v.lstrip().startswith(("=", "+", "-", "@")) else v
        writer.writerow(safe)
    return buf.getvalue().encode("utf-8")


def _create_only(path, payload):
    path = within(path)
    fd, tmp = tempfile.mkstemp(prefix=".step57_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(payload)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.link(tmp, path)  # atomically refuses overwrite
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def prepare(source=TRIAGE_DIR, dest=OUT):
    """Creates owner-only adjudication without any clinical source access."""
    src, target = within(source), within(dest)
    report_dest, records_dest = target / SUMMARY, target / DECISIONS
    if report_dest.exists() or records_dest.exists():
        raise FileExistsError("Step57 already exists; refusing overwrite")
    original_report = json.loads((src / REPORT).read_bytes())
    if (original_report.get("stage") != "STEP56_REFERENCE_VOCABULARY_COVERAGE_TRIAGE_ONLY"
        or original_report.get("patient_or_clinical_event_rows_read") != 0
        or original_report.get("Research_Network_ZIP_opened") is not False
        or original_report.get("clinical_codebook_approved") is not False
        or original_report.get("full_clinical_scan_enabled") is not False):
        raise ValueError("Step56 report not a safe reference-only source")
    input_blob = (src / CPT_QUEUE).read_bytes()
    rows = _csv_read(input_blob)
    if len(rows) != original_report.get("deferred_CPT_entries_for_targeted_external_review"):
        raise ValueError("Step56 queue size differs from reference-only status")
    decisions = adjudicate(rows)
    counts = dict(sorted(Counter(
        x["external_evidence_decision"] for x in decisions
    ).items()))
    out = {
        "stage": "STEP57_EXTERNAL_CPT_EVIDENCE_ADJUDICATION_REFERENCE_ONLY",
        "step56_queue_SHA256": hashlib.sha256(input_blob).hexdigest(),
        "local_private_queue_entries": len(decisions),
        "external_evidence_decisions": counts,
        "new_core_imaging_codes_added": 0,
        "local_unverified_CPT_labels_promoted": 0,
        "actual_procedure_utilization_observed": False,
        "patient_or_clinical_event_rows_read": 0,
        "Research_Network_ZIP_opened": False,
        "existing_review_files_overwritten": False,
        "clinical_codebook_approved": False,
        "data_use_approvals_changed": False,
        "full_clinical_scan_enabled": False,
    }
    private_folder(target)
    _create_only(records_dest, _csv_encode(decisions))
    _create_only(report_dest, (json.dumps(out, indent=2, sort_keys=True) + "\n").encode())
    print("STEP57: external code-meaning review of existing PRIVATE CPT queue.")
    print("Entries adjudicated:", out["local_private_queue_entries"])
    print("Decision counts:", out["external_evidence_decisions"])
    print("Private decisions:", records_dest)
    print("Private summary:", report_dest)
    print("CPT14 diagnostic code core unchanged; no clinical data scanned.")
    print("Institutional approvals unchanged. Real-source scan remains BLOCKED.")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare"])
    args = parser.parse_args()
    prepare()


if __name__ == "__main__":
    main()
