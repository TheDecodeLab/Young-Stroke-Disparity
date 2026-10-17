"""Step 28: explicitly gated expanded imaging-code extraction from EXISTING ZIP.

Default --plan reads ZIP directory metadata and completed index counts only.
--execute is blocked unless a local approval file attests to an exact
codebook/source fingerprint and signed-off study criteria. NO new TriNetX data.

No encounter ID is available; this produces private procedure CODE events
within +/-7 calendar days of a diagnosis date, NOT admission-level imaging.
All patient-level events stay in owner-only SQLite outside the repository.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from zipfile import ZipFile

import pandas as pd

try:
    from scripts.step19_21_reconstruct import (
        source_signature, manifest_rows, STAGES)
    from scripts.step18_diagnosis_index import ensure_private_dir
except ModuleNotFoundError:
    from step19_21_reconstruct import source_signature, manifest_rows, STAGES
    from step18_diagnosis_index import ensure_private_dir

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CODEBOOK = ROOT / "dataset/imaging_codebook_candidate_v1.csv"
STUDY_COHORT = "principal_I63_2018_2019_approx_age19_50_recognized_sex"
OLD = "imaging/step20_imaging_events.sqlite"
TARGET = "imaging_expanded/step28_imaging_events.sqlite"
MODALITIES = ("CT", "MRI", "CTA", "MRA")
ALLOWED_SYSTEMS = {"CPT", "HCPCS", "ICD-10-PCS"}


def codebook(path: Path) -> tuple[dict, str, list[dict]]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    expected = {"code_system", "code", "modality", "anatomy",
                "source_status", "short_label", "clinical_review"}
    if set(reader.fieldnames or ()) != expected:
        raise ValueError("Codebook must use the expected seven columns")
    result = {}
    audit = []
    for item in reader:
        fields = {k: v.strip() for k, v in item.items()}
        system, code, modality = fields["code_system"].upper(), fields["code"].upper(), fields["modality"].upper()
        if system not in ALLOWED_SYSTEMS or not re.fullmatch(r"[0-9A-Z.]+", code):
            raise ValueError("Unknown code system or invalid procedure code")
        if modality not in MODALITIES:
            raise ValueError("Unsupported imaging modality")
        valid_anatomy = {
            ("CT", "head"), ("MRI", "brain"),
            ("CTA", "head"), ("CTA", "neck"),
            ("MRA", "head"), ("MRA", "neck"),
        }
        if (modality, fields["anatomy"].lower()) not in valid_anatomy:
            raise ValueError("Unrecognized anatomical mapping in codebook")
        if fields["clinical_review"] not in {"pending", "approved"}:
            raise ValueError("Unrecognized clinical-review status")
        if fields["source_status"] not in {"historical", "review_candidate"}:
            raise ValueError("Unrecognized code provenance")
        key = (system, code)
        if key in result:
            raise ValueError("Duplicate code in procedure codebook")
        result[key] = modality
        audit.append({k: fields[k] for k in ("code_system", "code", "modality",
                                            "anatomy", "source_status", "clinical_review")})
    if not result or not all(m in result.values() for m in MODALITIES):
        raise ValueError("Every modality must have at least one code")
    # Old nine codes must remain present with their original assignments
    # so a new scan is testably a superset of the previous extraction.
    historical = {
        "70450": "CT", "70460": "CT", "70470": "CT", "70496": "CTA",
        "70544": "MRA", "70545": "MRA",
        "70551": "MRI", "70552": "MRI", "70553": "MRI"}
    for old_code, modality in historical.items():
        if result.get(("CPT", old_code)) != modality:
            raise ValueError("Historical CPT code missing or changed: " + old_code)
    return result, digest, audit


def complete_db(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing completed private database {path.name}")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as c:
        state = c.execute("SELECT value FROM scan_state WHERE key='scan_complete'").fetchone()
    if state != ("1",):
        raise ValueError(f"Refusing incomplete private database {path.name}")


def load_index(private: Path) -> dict:
    path = private / "demographics" / STAGES["cohort"]
    complete_db(path)
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as c:
        config = dict(c.execute("SELECT key,value FROM scan_state"))
        if (config.get("min_age"), config.get("max_age")) != ("19", "50"):
            raise ValueError("Saved cohort is not uniform age 19-50")
        cohort = {pid: date for pid, date in c.execute(
            "SELECT patient_id,index_date FROM eligible")}
    if not cohort:
        raise ValueError("No eligible diagnoses")
    return cohort


def validate_source(private: Path, zip_file: Path) -> tuple[dict, int]:
    if not zip_file.is_file():
        raise FileNotFoundError(zip_file)
    stored = private / "source_signature.json"
    if not stored.is_file():
        raise ValueError("Missing original source archive fingerprint")
    with ZipFile(zip_file) as zf:
        actual = source_signature(zf)
        declared = manifest_rows(zf, "procedure.csv")
    if actual != json.loads(stored.read_text(encoding="utf-8")):
        raise ValueError("Source ZIP does not match completed diagnosis index")
    return actual, declared


def plan(zip_file: Path, private_dir: Path, codebook_file: Path) -> dict:
    private = ensure_private_dir(private_dir)
    if not private.is_dir():
        raise ValueError("Private location must exist")
    complete_db(private / "diagnosis" / STAGES["diagnosis"])
    complete_db(private / OLD)
    cohort = load_index(private)
    signature, declared = validate_source(private, zip_file)
    mapping, digest, rows = codebook(codebook_file)
    return {
        "stage": "STEP28_PREFLIGHT_ONLY",
        "requires_review": True,
        "approval_status": "NOT_APPROVED",
        "candidate_codes": rows,
        "number_of_candidate_codes": len(mapping),
        "codebook_sha256": digest,
        "archive_members_sha256": signature["archive_members_sha256"],
        "source_procedure_rows_declared": declared,
        "private_indexed_age_19_50_patients": len(cohort),
        "study_population_identifier": STUDY_COHORT,
        "planned_primary_window_days_each_side": 1,
        "maximum_extraction_window_days_each_side": 7,
        "procedure_rows_scanned": 0,
        "clinical_inference_allowed": False,
        "warning": "Preflight does not approve code definitions or produce admissions/clinical utilization."
    }


def check_approval(approval_file: Path, manifest: dict) -> None:
    if approval_file is None:
        raise ValueError("--execute requires --approval with investigator and clinician decisions")
    resolved = approval_file.expanduser().resolve()
    if resolved == ROOT.resolve() or ROOT.resolve() in resolved.parents:
        raise ValueError("Approval file must remain outside the Git repository")
    approval = json.loads(resolved.read_text(encoding="utf-8"))
    required = {
        "decision": "approved",
        "codebook_sha256": manifest["codebook_sha256"],
        "archive_members_sha256": manifest["archive_members_sha256"],
        "study_population_identifier": STUDY_COHORT,
        "primary_window_days_each_side": 1,
        "maximum_extraction_window_days_each_side": 7,
        "recorded_code_outcome_only": True,
        "no_verified_encounter_claims": True,
        "data_use_review_complete": True,
    }
    if any(approval.get(k) != value for k, value in required.items()):
        raise ValueError("Approval does not match source, codebook or fixed-data protocol")
    for field in ("investigator_reviewer", "clinical_reviewer", "approval_date"):
        value = approval.get(field)
        if not isinstance(value, str) or not value.strip() or value.strip().upper() in {"TBD", "PENDING", "YOUR_NAME"}:
            raise ValueError(f"Missing explicit approval field: {field}")
    # All individual codebook rows must be marked approved before expensive execution.
    if not all(item["clinical_review"] == "approved" for item in manifest["candidate_codes"]):
        raise ValueError("Clinical review pending in the codebook; full extraction blocked")


def select_codes(chunk: pd.DataFrame, index: dict, mapping: dict) -> list[tuple]:
    """Filter BEFORE any date parsing; dates tied only to eligible index patients."""
    required = {"patient_id", "code", "code_system", "date"}
    if not required.issubset(chunk.columns):
        raise ValueError("Procedure columns missing")
    sub = chunk.loc[chunk["patient_id"].isin(index), ["patient_id", "code", "code_system", "date"]].copy()
    if sub.empty:
        return []
    sub["code"] = sub["code"].str.strip().str.upper()
    sub["code_system"] = sub["code_system"].str.strip().str.upper()
    sub["modality"] = [mapping.get((cs, code)) for cs, code in
                       zip(sub["code_system"], sub["code"])]
    sub = sub.loc[sub["modality"].notna()]
    if sub.empty:
        return []
    when = pd.to_datetime(sub["date"], format="%Y%m%d", errors="coerce")
    ref = pd.to_datetime(sub["patient_id"].map(index), format="%Y%m%d", errors="coerce")
    difference = (when - ref).dt.days
    sub = sub.loc[difference.between(-7, 7)].copy()
    sub["offset_days"] = difference.loc[sub.index].astype(int)
    return [tuple(x) for x in sub[["patient_id", "modality", "code_system", "code",
                                    "date", "offset_days"]].itertuples(index=False, name=None)]


def compare_legacy(private: Path, con: sqlite3.Connection) -> int:
    """Every historical modality/day receipt must persist in expanded index."""
    old = private / OLD
    complete_db(old)
    with sqlite3.connect(old.as_uri() + "?mode=ro", uri=True) as original:
        previous = set(original.execute(
            "SELECT patient_id,modality,procedure_date FROM imaging_event"))
    current = set(con.execute(
        "SELECT patient_id,modality,procedure_date FROM event"))
    if not previous.issubset(current):
        raise ValueError("New codebook extraction LOST original patient/modality/day matches")
    return len(previous)


def aggregate_window(con: sqlite3.Connection, index_n: int, days: int) -> dict:
    tuples = list(con.execute(
        "SELECT patient_id,modality FROM event WHERE offset_days BETWEEN ? AND ? "
        "GROUP BY patient_id,modality", (-days, days)))
    flags = {}
    for pid, modality in tuples:
        flags.setdefault(pid, set()).add(modality)
    result = {"total": index_n}
    for modality in MODALITIES:
        result[modality] = sum(modality in f for f in flags.values())
    only_ct = ct_plus = advanced_no_ct = 0
    for modalities in flags.values():
        ct = "CT" in modalities
        advanced = bool(modalities.intersection(("MRI", "CTA", "MRA")))
        only_ct += bool(ct and not advanced)
        ct_plus += bool(ct and advanced)
        advanced_no_ct += bool(not ct and advanced)
    result.update({"CT only": only_ct, "CT + additional": ct_plus,
                   "Additional without CT": advanced_no_ct,
                   "None of four": index_n - len(flags)})
    if sum(result[x] for x in ("CT only", "CT + additional",
             "Additional without CT", "None of four")) != index_n:
        raise ValueError("Imaging count partition broken")
    # Conservative: if any nonzero cell would be <11, suppress entire
    # breakdown in this window to avoid a trivially recoverable residual.
    if any(0 < n < 11 for k, n in result.items() if k != "total"):
        return {"total": index_n, "suppressed": True}
    result["suppressed"] = False
    return result



def aggregate_anatomic_window(
    con: sqlite3.Connection, index_n: int, days: int, code_rows: list[dict]
) -> dict:
    """Head-only primary versus head+neck sensitivity, using saved exact codes.

    Internal aggregate only. Suppresses the ENTIRE comparison when rare
    positive cells or small differences between nested endpoint choices
    could reveal an otherwise suppressed count. A release still needs
    cross-table disclosure review.
    """
    lookup = {
        (item["code_system"].upper(), item["code"].upper()):
        (item["modality"].upper(), item["anatomy"].lower())
        for item in code_rows
    }
    allowed = {
        ("CT", "head"), ("MRI", "brain"), ("CTA", "head"), ("CTA", "neck"),
        ("MRA", "head"), ("MRA", "neck"),
    }
    if any(entry not in allowed for entry in lookup.values()):
        raise ValueError("Anatomical modality assignment is not approved by the schema")

    rows = con.execute(
        "SELECT patient_id,code_system,code,modality FROM event "
        "WHERE offset_days BETWEEN ? AND ? GROUP BY patient_id,code_system,code,modality",
        (-days, days),
    )
    anatomy_by_patient = {}
    for pid, system, code, modality in rows:
        canonical = lookup.get((system.upper(), code.upper()))
        if canonical is None or canonical[0] != modality.upper():
            raise ValueError("Extracted event does not match approved codebook")
        anatomy_by_patient.setdefault(pid, set()).add(canonical)
    head_counts = {"total": index_n, "CT": 0, "MRI": 0, "CTA": 0, "MRA": 0}
    wide_counts = dict(head_counts)
    head_classes = {"CT only": 0, "CT + additional": 0,
                    "Additional without CT": 0, "None of four": 0}
    wide_classes = dict(head_classes)
    neck_only = {"CTA neck without CTA head": 0,
                 "MRA neck without MRA head": 0}

    def category(present: set) -> str:
        ct = "CT" in present
        advanced = bool(present & {"MRI", "CTA", "MRA"})
        if ct and not advanced:
            return "CT only"
        if ct and advanced:
            return "CT + additional"
        if advanced:
            return "Additional without CT"
        return "None of four"

    for events in anatomy_by_patient.values():
        head = {mod for mod, anatomy in events
                if (mod, anatomy) in {("CT", "head"), ("MRI", "brain"),
                                      ("CTA", "head"), ("MRA", "head")}}
        wide = {mod for mod, _ in events}
        for name, present, classes in (
            ("head", head, head_classes), ("wide", wide, wide_classes)
        ):
            for modality in MODALITIES:
                if modality in present:
                    (head_counts if name == "head" else wide_counts)[modality] += 1
            classes[category(present)] += 1
        if ("CTA", "neck") in events and ("CTA", "head") not in events:
            neck_only["CTA neck without CTA head"] += 1
        if ("MRA", "neck") in events and ("MRA", "head") not in events:
            neck_only["MRA neck without MRA head"] += 1

    # An individual with no saved matched code belongs to both 'none' groups.
    head_classes["None of four"] += index_n - len(anatomy_by_patient)
    wide_classes["None of four"] += index_n - len(anatomy_by_patient)
    for counts, classes in ((head_counts, head_classes), (wide_counts, wide_classes)):
        counts.update(classes)
        if sum(classes.values()) != index_n:
            raise ValueError("Anatomic categories do not reconcile")
    all_cells = [*head_counts.values(), *wide_counts.values(), *neck_only.values()]
    all_cells += [abs(head_counts[k] - wide_counts[k])
                  for k in ("CT", "MRI", "CTA", "MRA", *head_classes.keys())]
    if any(0 < int(v) < 11 for v in all_cells):
        return {"total": index_n, "suppressed": True}
    return {
        "total": index_n, "suppressed": False,
        "head_only_primary": head_counts,
        "head_plus_neck_sensitivity": wide_counts,
        "neck_without_head_cta_mra": neck_only,
    }


def execute(zip_file: Path, private_dir: Path, codebook_file: Path,
            approval_file: Path, chunk_rows: int = 150000) -> dict:
    if not 100 <= chunk_rows <= 2000000:
        raise ValueError("Chunk size outside supported range")
    manifest = plan(zip_file, private_dir, codebook_file)
    check_approval(approval_file, manifest)
    private = ensure_private_dir(private_dir)
    output_dir = ensure_private_dir(private / "imaging_expanded")
    target = private / TARGET
    partial = target.with_name(target.name.replace(".sqlite", ".partial.sqlite"))
    if target.exists() or partial.exists():
        raise FileExistsError("Refuse to overwrite previous or incomplete expanded index")
    index = load_index(private)
    mapping, digest, code_rows = codebook(codebook_file)
    connection = sqlite3.connect(partial)
    os.chmod(partial, 0o600)
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("""CREATE TABLE event(
        patient_id TEXT NOT NULL, modality TEXT NOT NULL, code_system TEXT NOT NULL,
        code TEXT NOT NULL, procedure_date TEXT NOT NULL, offset_days INTEGER NOT NULL,
        PRIMARY KEY(patient_id,code_system,code,procedure_date))""")
    connection.execute("CREATE TABLE scan_state(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    connection.execute("INSERT INTO scan_state VALUES('scan_complete','0')")
    connection.commit()
    scanned = 0
    try:
        with ZipFile(zip_file) as zf:
            expected = manifest_rows(zf, "procedure.csv")
            with zf.open("procedure.csv") as infile:
                reader = pd.read_csv(infile, dtype="string",
                                     usecols=["patient_id", "code", "code_system", "date"],
                                     chunksize=chunk_rows, keep_default_na=False)
                for batch, chunk in enumerate(reader, start=1):
                    scanned += len(chunk)
                    rows = select_codes(chunk, index, mapping)
                    if rows:
                        connection.executemany(
                            "INSERT OR IGNORE INTO event VALUES (?,?,?,?,?,?)", rows)
                    connection.commit()
                    if batch % 100 == 0:
                        print(f"Step 28: scanned {scanned:,} procedure rows", flush=True)
            if scanned != expected:
                raise ValueError("Source procedure scan differs from ZIP manifest")
        retained_legacy = compare_legacy(private, connection)
        report_windows = {str(d): aggregate_window(connection, len(index), d)
                          for d in (0, 1, 3, 7)}
        anatomic_windows = {str(d): aggregate_anatomic_window(
            connection, len(index), d, code_rows) for d in (0, 1, 3, 7)}
        n = connection.execute("SELECT COUNT(*) FROM event").fetchone()[0]
        connection.execute("INSERT INTO scan_state VALUES('source_rows_scanned',?)",
                           (str(scanned),))
        connection.execute("INSERT INTO scan_state VALUES('codebook_sha256',?)",
                           (digest,))
        connection.execute("INSERT INTO scan_state VALUES('archive_members_sha256',?)",
                           (manifest["archive_members_sha256"],))
        connection.execute("UPDATE scan_state SET value='1' WHERE key='scan_complete'")
        connection.commit()
        connection.close()
        partial.rename(target)
    except Exception:
        connection.close()
        raise
    return {
        "stage": "STEP28_EXPANDED_CODE_EXTRACTION_TEMPORAL_PROXY",
        "source_procedure_rows_scanned": scanned,
        "manifest_row_count_verified": True,
        "approved_codebook_sha256": digest,
        "complete_private_database_file": target.name,
        "retained_legacy_patient_modality_days": retained_legacy,
        "matched_code_specific_patient_days": n,
        "windows_inclusive_days_each_side": report_windows,
        "anatomic_profiles_by_window": anatomic_windows,
        "aggregate_disclosure_review_required": True,
        "primary_recorded_vascular_endpoint": "CTA/MRA head only",
        "sensitivity_vascular_endpoint": "CTA/MRA head or neck",
        "eligible_diagnosis_first_patients": len(index),
        "encounter_validated": False,
        "ready_for_manuscript_inference": False,
        "warning": "These are recorded imaging codes near I63 diagnosis, not admissions or performed imaging."
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true",
                      help="Safe default: inspect metadata and proposed codes; scan zero clinical rows")
    mode.add_argument("--execute", action="store_true",
                      help="Full billion-row scan: requires formal matching clinical/data-use approval")
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--codebook", type=Path, default=DEFAULT_CODEBOOK)
    p.add_argument("--approval", type=Path)
    p.add_argument("--chunk-rows", type=int, default=150000)
    p.add_argument("--output", type=Path,
                   default=ROOT / "results/phase1/step28_codebook_plan.json")
    args = p.parse_args()
    if args.plan:
        report = plan(args.zip, args.private_dir, args.codebook)
    else:
        report = execute(args.zip, args.private_dir, args.codebook,
                         args.approval, args.chunk_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("Aggregate-only output:", args.output)
    print("Original clinical rows scanned:", report.get("source_procedure_rows_scanned", 0))


if __name__ == "__main__":
    main()
