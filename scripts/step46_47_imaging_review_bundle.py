#!/usr/bin/env python3
"""Steps 46-47: prepare private imaging review, then validate clinician sign-off.

PREPARE reads only the Step42 LOCAL_ONLY terminology worksheet and aggregate
status. FINALIZE is a separate, manually authorized action after clinical
review; it never changes institutional approval flags or scans clinical data.
All generated artifacts are inside this clone's gitignored results/phase1/.
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
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

if __package__:
    from .step42_neuroimaging_vocabulary import CPT_ANCHORS, ROOT
    from .step45_full_cohort_reconstruction import CATEGORIES, CODEBOOK
else:
    from step42_neuroimaging_vocabulary import CPT_ANCHORS, ROOT
    from step45_full_cohort_reconstruction import CATEGORIES, CODEBOOK

PHASE1 = ROOT / "results" / "phase1"
SOURCE_CSV = PHASE1 / "step42_neuroimaging_codebook_LOCAL_ONLY.csv"
SOURCE_JSON = PHASE1 / "step42_neuroimaging_vocabulary_status.json"
DEST = PHASE1 / "full_reconstruction_private" / "imaging_review"
INVENTORY = "all_reference_candidates_LOCAL_ONLY.csv"
PRIORITY = "clinical_review_priority_LOCAL_ONLY.csv"
SIGNOFF = "imaging_review_signoff_LOCAL_ONLY.json"
QUESTIONS = "imaging_reviewer_brief_LOCAL_ONLY.md"
STATUS = "imaging_review_preparation_status_LOCAL_ONLY.json"
FINAL_STATUS = "imaging_review_validation_status_LOCAL_ONLY.json"
REVIEW_COLS = (
    "review_id", "review_priority", "code_system", "code", "reference_description",
    "reference_path", "automated_candidate_NOT_APPROVED", "discovery_basis",
    "clinician_decision_INCLUDE_EXCLUDE_DEFER", "reviewed_category",
    "performed_procedure_confirmed_yes_no", "valid_for_2018_2019_yes_no",
    "anatomy_resolved_yes_no", "clinical_rationale", "evidence_reference",
    "reviewer", "review_date",
)
REQUIRED_SOURCE = (
    "code_system", "code", "code_description", "path",
    "candidate_category_NOT_VALIDATED", "discovery_reason",
    "reviewer_include_LEAVE_BLANK", "reviewer_notes_LEAVE_BLANK",
)
STAGE = "STEP42_REFERENCE_ONLY_NEUROIMAGING_CODE_DISCOVERY"
SIGNOFF_FIELDS = (
    "clinical_code_review_signed_off", "full_candidate_inventory_scope_considered",
    "procedure_performed_semantics_checked", "coding_system_coverage_checked",
    "study_period_2018_2019_coverage_checked", "conflicting_code_meanings_resolved",
)
FINAL_HEADER = "code_system,code,category,record_meaning,reviewer,review_date\n"
VALID_DECISIONS = {"", "include", "exclude", "defer"}
VALID_YN = {"yes", "no", ""}
SYSTEMS = {"CPT", "SNOMED", "HCPCS", "ICD-10-PCS", "ICD-9-CM"}


def within(path: Path, base=PHASE1) -> Path:
    allowed = ROOT.resolve() / "results" / "phase1"
    if PHASE1.resolve() != allowed:
        raise ValueError("results/phase1 must not be a symlink escape")
    p = path.expanduser().resolve()
    if p != allowed and allowed not in p.parents:
        raise ValueError("All local inputs/outputs must be inside cloned repo results/phase1/")
    return p


def private_folder(path):
    out = within(path)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Refuse to use a shared directory for clinical annotations.
    if out.stat().st_mode & 0o077:
        raise PermissionError("Review directory must be owner-only (chmod 700)")
    return out


def atomic_write(path, payload):
    path = within(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".step46_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(payload)
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def csv_cell(value):
    value = str(value or "")
    # CSV is opened by reviewers in spreadsheet applications.
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def csv_blob(rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, REVIEW_COLS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: csv_cell(row.get(k, "")) for k in REVIEW_COLS})
    return buf.getvalue().encode("utf-8")


def identity(row):
    values = [
        (row.get("code_system") or "").strip().upper(),
        (row.get("code") or "").strip().upper(),
        (row.get("code_description") or "").strip(),
        (row.get("path") or "").strip(),
        (row.get("candidate_category_NOT_VALIDATED") or "").strip(),
    ]
    return hashlib.sha256(
        json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_source(csv_path=SOURCE_CSV, status_path=SOURCE_JSON):
    cpath, jpath = within(csv_path), within(status_path)
    blob = jpath.read_bytes()
    status = json.loads(blob)
    if (status.get("stage") != STAGE or
            status.get("source_is_reference_terminology_only") is not True or
            status.get("clinical_event_rows_examined") != 0):
        raise ValueError("Step42 reference-only lineage invalid")
    with cpath.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != REQUIRED_SOURCE:
            raise ValueError("Step42 source worksheet header mismatch")
        source_rows = list(reader)
    if len(source_rows) != status.get("candidate_rows_n"):
        raise ValueError("Step42 number of source rows differs from status")
    counts = dict(Counter(
        row["candidate_category_NOT_VALIDATED"] for row in source_rows
    ))
    if counts != status.get("candidate_category_rows"):
        raise ValueError("Step42 source category counts do not reconcile")
    reasons = dict(Counter(row["discovery_reason"] for row in source_rows))
    if reasons != status.get("discovery_reason_rows"):
        raise ValueError("Step42 discovery reasons do not reconcile")
    indexed = {}
    for row in source_rows:
        ident = identity(row)
        if ident in indexed:
            raise ValueError("Duplicate Step42 terminology identity")
        indexed[ident] = row
    return indexed, hashlib.sha256(blob).hexdigest()


def review_entry(ident, source):
    system = (source["code_system"] or "").strip().upper()
    code = (source["code"] or "").strip().upper()
    anchor = system == "CPT" and code in CPT_ANCHORS
    return {
        "review_id": ident,
        "review_priority": "HISTORICAL_CPT_ANCHOR_VERIFY" if anchor else (
            "MIXED_ANATOMY_REVIEW" if source["candidate_category_NOT_VALIDATED"] ==
            "AMBIGUOUS_HEAD_AND_NECK" else "ADDITIONAL_REFERENCE_CANDIDATE"),
        "code_system": system,
        "code": code,
        "reference_description": source["code_description"],
        "reference_path": source["path"],
        "automated_candidate_NOT_APPROVED": source["candidate_category_NOT_VALIDATED"],
        "discovery_basis": source["discovery_reason"],
        "clinician_decision_INCLUDE_EXCLUDE_DEFER": "",
        "reviewed_category": "",
        "performed_procedure_confirmed_yes_no": "",
        "valid_for_2018_2019_yes_no": "",
        "anatomy_resolved_yes_no": "",
        "clinical_rationale": "",
        "evidence_reference": "",
        "reviewer": "",
        "review_date": "",
    }


def select_review_subset(entries, per_category=5, ambiguous_limit=5):
    """Convenience subset only; full inventory is mandatory for scope review."""
    anchors = sorted(
        (x for x in entries if x["review_priority"] == "HISTORICAL_CPT_ANCHOR_VERIFY"),
        key=lambda x: (x["automated_candidate_NOT_APPROVED"], x["code_system"], x["code"]),
    )
    selected = anchors[:]
    seen = {x["review_id"] for x in anchors}
    code_system_order = {"CPT": 0, "SNOMED": 1, "HCPCS": 2, "ICD-10-PCS": 3, "ICD-9-CM": 4}
    others = sorted(
        (x for x in entries if x["review_id"] not in seen),
        key=lambda x: (code_system_order.get(x["code_system"], 9),
                       x["code_system"], x["code"], x["review_id"]),
    )
    categories = defaultdict(list)
    for x in others:
        categories[x["automated_candidate_NOT_APPROVED"]].append(x)
    for category in sorted(categories):
        limit = ambiguous_limit if category == "AMBIGUOUS_HEAD_AND_NECK" else per_category
        selected.extend(categories[category][:limit])
    return selected


def questions_text(n_source, n_first, report_digest):
    return f"""# Imaging codebook: clinical reviewer worksheet (PRIVATE)

This packet was generated only from the Research Network reference terminology.
It contains **no patients, encounters, clinical frequencies or imaging utilization**.
Step42 status SHA-256: {report_digest}

Source candidate entries: {n_source}; convenience first-review entries: {n_first}.
The first-review sheet is NOT a comprehensive or clinically approved codebook.
Consult the complete inventory before signing off source-code-system coverage.

## For the study neurologist/neuroradiologist and data steward

1. For every selected CPT/SNOMED/HCPCS/ICD code, what is the precise
   2018-2019 meaning? Does a record represent a **performed examination**
   rather than an order, history, result, referral, or billing status?
2. Distinguish **MRI brain** from **MRA head/neck**, **CTA head** from
   **CTA neck**, and CT head from vascular imaging. Resolve any mixed
   head+neck descriptions only using external authoritative definitions.
3. Could HCOs use local codes or imaging pathways not described by these
   reference candidates? Confirm which source code systems are actually
   usable for the Research Network procedure table.
4. Are any code descriptions nonspecific or ambiguous? Mark those
   **exclude** or **defer**, not include, until clinical review resolves them.
5. Can the final codebook be defended for **both co-primary cohorts**:
   ages 18-50 and original men 18-52 / women 18-54?

## How to fill clinical_review_priority_LOCAL_ONLY.csv

Only edit the explicit review fields at the right. Use:
- clinician_decision_INCLUDE_EXCLUDE_DEFER: include, exclude, or defer
- reviewed_category: MRI_BRAIN, CTA_HEAD, CTA_NECK, MRA_HEAD, MRA_NECK, CT_HEAD
- performed_procedure_confirmed_yes_no: yes ONLY with performed-procedure evidence
- valid_for_2018_2019_yes_no: yes ONLY if the code is appropriate for the study years
- anatomy_resolved_yes_no: yes if the anatomy and modality are clinically resolved
- clinical_rationale, evidence_reference, reviewer, review_date: required for included rows

An included code must have all inclusion evidence fields. If its
auto-candidate category is ambiguous or the reviewer overrides the
suggested category, explain why in clinical_rationale/evidence_reference.

**Do not set the signoff JSON booleans to true without documented review.**
Finalization is optional, fails closed until signed off and NEVER alters
Step45 approvals_LOCAL_ONLY.json. The review inventory remains private;
share only through an institution-approved route after data-owner review.
"""


def prepare(source=SOURCE_CSV, status=SOURCE_JSON, output=DEST,
            per_category=5, ambiguous_limit=5):
    if not (1 <= per_category <= 20 and 1 <= ambiguous_limit <= 20):
        raise ValueError("Review sampling limits must be between 1 and 20")
    indexed, report_digest = load_source(source, status)
    out = within(output)
    output_names = [INVENTORY, PRIORITY, SIGNOFF, QUESTIONS, STATUS]
    if any((out / x).exists() for x in output_names):
        raise FileExistsError("Review files already exist; refusing to erase clinical annotations")
    private_folder(out)
    entries = [review_entry(k, row) for k, row in indexed.items()]
    entries.sort(key=lambda x: (
        x["review_priority"], x["automated_candidate_NOT_APPROVED"],
        x["code_system"], x["code"], x["review_id"]
    ))
    first = select_review_subset(entries, per_category, ambiguous_limit)
    if len({x["review_id"] for x in first}) != len(first):
        raise ValueError("Review first subset has duplicate identifiers")
    sig = {
        **{key: False for key in SIGNOFF_FIELDS},
        "reviewer_name": "", "review_date": "", "review_authority_reference": "",
        "source_step42_status_sha256": report_digest,
        "scope_notes": "",
    }
    summary = {
        "stage": "STEP46_PRIVATE_IMAGING_REVIEW_PREPARED",
        "clinical_event_rows_read": 0,
        "full_reference_candidate_entries_preserved": len(entries),
        "first_review_entries": len(first),
        "historical_CPT_anchors_for_verification": sum(
            x["review_priority"] == "HISTORICAL_CPT_ANCHOR_VERIFY" for x in first
        ),
        "source_step42_status_sha256": report_digest,
        "codebook_clinically_validated": False,
        "real_scan_approved": False,
    }
    atomic_write(out / INVENTORY, csv_blob(entries))
    atomic_write(out / PRIORITY, csv_blob(first))
    atomic_write(out / QUESTIONS, questions_text(len(entries), len(first), report_digest).encode("utf-8"))
    atomic_write(out / SIGNOFF, (json.dumps(sig, indent=2, sort_keys=True) + "\n").encode())
    atomic_write(out / STATUS, (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode())
    print("Prepared full private inventory, first-review sheet, reviewer brief and FALSE signoff template.")
    print("Reference entries:", len(entries), "first review:", len(first))
    print("Private review directory:", out)
    print("No clinical records read. Step45 approvals and codebook unchanged.")
    return summary


def finalize(source=SOURCE_CSV, status=SOURCE_JSON, output=DEST,
             review=None, signoff=None, target=CODEBOOK):
    """Optional, only after documented review; never touches approvals JSON."""
    out = private_folder(output)
    review = within(review or (out / PRIORITY))
    signed_file = within(signoff or (out / SIGNOFF))
    destination = within(target)
    indexed, report_digest = load_source(source, status)
    signing = json.loads(signed_file.read_text(encoding="utf-8"))
    if any(signing.get(x) is not True for x in SIGNOFF_FIELDS):
        raise PermissionError("Clinical codebook finalization blocked: signed review gates incomplete")
    if signing.get("source_step42_status_sha256") != report_digest:
        raise PermissionError("Step42 source changed since the clinical review")
    for k in ("reviewer_name", "review_date", "review_authority_reference", "scope_notes"):
        if not (isinstance(signing.get(k), str) and signing[k].strip()):
            raise PermissionError("Document clinical reviewer/date, authority and candidate scope rationale")
    try:
        date.fromisoformat(signing["review_date"])
    except ValueError:
        raise PermissionError("Signoff review_date must be YYYY-MM-DD")
    with review.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != REVIEW_COLS:
            raise ValueError("Review worksheet columns altered")
        reviewed = list(reader)
    approved = []
    approved_keys = set()
    ids = set()
    for item in reviewed:
        identity_value = (item["review_id"] or "").strip()
        if identity_value in ids or identity_value not in indexed:
            raise ValueError("Duplicate or unrecognized review_id in clinician worksheet")
        ids.add(identity_value)
        source_row = indexed[identity_value]
        key = (
            source_row["code_system"].strip().upper(),
            source_row["code"].strip().upper(),
        )
        if (item["code_system"].strip().upper(), item["code"].strip().upper()) != key:
            raise ValueError("Code/system edited; terminology provenance mismatch")
        decision = (item["clinician_decision_INCLUDE_EXCLUDE_DEFER"] or "").strip().lower()
        if decision not in VALID_DECISIONS:
            raise ValueError("Invalid include/exclude/defer decision")
        if decision != "include":
            continue
        cat = (item["reviewed_category"] or "").strip().upper()
        status_fields = (
            (item["performed_procedure_confirmed_yes_no"] or "").strip().lower(),
            (item["valid_for_2018_2019_yes_no"] or "").strip().lower(),
            (item["anatomy_resolved_yes_no"] or "").strip().lower(),
        )
        if cat not in CATEGORIES or any(x != "yes" for x in status_fields):
            raise PermissionError("Included code lacks reviewed category, performed meaning, years or anatomy")
        if any(not (item[k] or "").strip() for k in (
            "clinical_rationale", "evidence_reference", "reviewer", "review_date"
        )):
            raise PermissionError("Included code needs clinician rationale, reference, reviewer and date")
        try:
            date.fromisoformat(item["review_date"].strip())
        except ValueError:
            raise PermissionError("Included code review_date must be YYYY-MM-DD")
        candidate = source_row["candidate_category_NOT_VALIDATED"].strip()
        if (candidate == "AMBIGUOUS_HEAD_AND_NECK" or cat != candidate):
            if len(item["clinical_rationale"].strip()) < 15:
                raise PermissionError("Mixed or overridden anatomy needs a substantial clinical rationale")
        if key in approved_keys:
            raise ValueError("Duplicate or conflicting code_system/code among included codes")
        if (key[0] not in SYSTEMS or not re.fullmatch(r"[A-Z0-9._-]{1,60}", key[1])):
            raise ValueError("Unsafe or unsupported code format for Step45 codebook")
        approved_keys.add(key)
        approved.append({
            "code_system": key[0], "code": key[1], "category": cat,
            "record_meaning": "performed", "reviewer": item["reviewer"].strip(),
            "review_date": item["review_date"].strip(),
        })
    if not approved:
        raise PermissionError("No reviewer-included performed imaging codes: cannot finalize")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.exists():
        # The Step45 template exists already, but must be exactly untouched.
        if destination.read_text(encoding="utf-8-sig") != FINAL_HEADER:
            raise FileExistsError("Existing Step45 codebook has content; never overwrite manual changes")
    output_buf = io.StringIO(newline="")
    writer = csv.DictWriter(
        output_buf, ("code_system","code","category","record_meaning","reviewer","review_date"),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(sorted(approved, key=lambda x: (x["category"],x["code_system"],x["code"])))
    blob = output_buf.getvalue().encode("utf-8")
    atomic_write(destination, blob)
    summary = {
        "stage": "STEP47_CLINICAL_CODEBOOK_VALIDATED_FOR_STEP45_INPUT_ONLY",
        "source_step42_status_sha256": report_digest,
        "clinical_review_signoff_supplied": True,
        "included_code_entries": len(approved),
        "clinical_event_rows_read": 0,
        "step45_institutional_approval_flags_changed": False,
        "full_scan_executed": False,
        "external_release_approved": False,
        "codebook_SHA256": hashlib.sha256(blob).hexdigest(),
    }
    atomic_write(out / FINAL_STATUS, (json.dumps(summary, indent=2, sort_keys=True)+"\n").encode())
    print("Created local Step45-format codebook from explicitly included, signed-off codes.")
    print("Step45 institutional approvals remain unchanged; real-data scan still blocked.")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    prep = actions.add_parser("prepare", help="Safe: reference-only local reviewer bundle")
    prep.add_argument("--per-category", type=int, default=5)
    prep.add_argument("--ambiguous-limit", type=int, default=5)
    actions.add_parser("finalize", help="Only after explicit clinical review/signoff; no clinical scan")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(per_category=args.per_category, ambiguous_limit=args.ambiguous_limit)
    else:
        finalize()


if __name__ == "__main__":
    main()
