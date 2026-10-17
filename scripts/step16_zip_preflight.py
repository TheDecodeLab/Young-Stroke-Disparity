"""Step 16: bounded, read-only ZIP source preflight without extraction.

Read all archive member headers, then only the first N records from the
three identified source tables. Sample results are NOT representative and
are NEVER a research cohort. Patient IDs, postal codes and row-level dates
are not read into the sample, printed or written to the aggregate JSON.
Use only on authorized local TriNetX ZIP archives.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import io
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo

import pandas as pd


def safe_member_header(zf: ZipFile, info: ZipInfo, limit: int = 65536) -> list[str] | None:
    """Decode at most the first 64KiB of a CSV or TSV member header."""
    ext = PurePosixPath(info.filename).suffix.lower()
    if ext not in (".csv", ".tsv"):
        return None
    with zf.open(info, "r") as f:
        first = f.readline(limit + 1)
    if len(first) > limit or (first and not first.endswith((b"\n", b"\r")) and info.file_size > len(first)):
        raise ValueError("Header exceeds bound")
    sep = "," if ext == ".csv" else "\t"
    return next(csv.reader(io.StringIO(first.decode("utf-8-sig", errors="replace")), delimiter=sep), [])


ROOT = Path(__file__).resolve().parents[1]
ROLE_FILES = {"diagnoses": "diagnosis.csv", "procedures": "procedure.csv", "demographics": "patient.csv"}
REQUIRED = {
    "diagnoses": {"patient_id", "code_system", "code", "principal_diagnosis_indicator", "date"},
    "procedures": {"patient_id", "code_system", "code", "date"},
    "demographics": {"patient_id", "sex", "race", "ethnicity", "year_of_birth"},
}
# Read only fields useful for category / format checks, not identifiers.
SAMPLE_FIELDS = {
    "diagnoses": ("code_system", "code", "date", "principal_diagnosis_indicator"),
    "procedures": ("code_system", "code", "date"),
    "demographics": ("sex", "race", "ethnicity", "year_of_birth"),
}
ENCOUNTER_IDENTIFIER_FIELDS = {
    "encounter_id", "encounterid", "encounter_number", "encounter_num",
    "visit_id", "visitid", "visit_number", "visit_num",
    "visit_occurrence_id", "admission_id", "admission_number",
    "hospitalization_id", "hospital_stay_id",
}


def is_encounter_identifier(name: str) -> bool:
    """Distinguish linkage IDs from descriptive fields like reason_for_visit."""
    value = name.strip().lower()
    return value in ENCOUNTER_IDENTIFIER_FIELDS


def _date_patterns(col: pd.Series) -> dict:
    s = col.astype("string").str.strip()
    missing = s.isna() | s.eq("")
    compact = s.str.fullmatch(r"\d{8}").fillna(False)
    iso = s.str.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[ T].*)?").fillna(False)
    return {
        "missing": int(missing.sum()),
        "compact_yyyymmdd": int(compact.sum()),
        "iso_like": int(iso.sum()),
        "other_nonmissing": int((~missing & ~compact & ~iso).sum()),
    }


def _categorical(s: pd.Series, allowed: int = 10) -> dict[str, int]:
    """Show only frequent non-identifying categorical values."""
    counts = Counter(s.astype("string").str.strip().fillna("(missing)").tolist())
    ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return {str(k)[:80]: int(v) for k, v in ordered if v >= 11 and k != ""} if len(ordered) <= allowed else {
        str(k)[:80]: int(v) for k, v in ordered[:allowed] if v >= 11 and k != ""
    }


def sample_summary(role: str, frame: pd.DataFrame) -> dict:
    """Summaries are sample diagnostics, never population statistics."""
    if role not in SAMPLE_FIELDS:
        raise ValueError("Unsupported role")
    wanted = set(SAMPLE_FIELDS[role])
    if missing := wanted - set(frame.columns):
        raise ValueError(f"Missing sampled fields: {sorted(missing)}")
    out = {"sample_rows_read": int(len(frame)), "sample_is_nonrepresentative": True}
    if "date" in frame:
        out["date_formats"] = _date_patterns(frame["date"])
    if "code_system" in frame:
        out["common_code_system_values"] = _categorical(frame["code_system"])
    if role == "diagnoses":
        out["principal_indicator_values"] = _categorical(frame["principal_diagnosis_indicator"])
        code = frame["code"].astype("string").str.strip().str.upper()
        out["I63_family_in_sample_n"] = int(code.str.fullmatch(r"I63(?:\..+)?").fillna(False).sum())
    elif role == "procedures":
        code = frame["code"].astype("string").str.strip()
        out["brain_CT_CPT_in_sample_n"] = int(code.isin(["70450", "70460", "70470"]).sum())
        out["head_CTA_CPT_in_sample_n"] = int(code.eq("70496").sum())
        out["brain_MRI_CPT_in_sample_n"] = int(code.isin(["70551", "70552", "70553"]).sum())
    else:
        out["sex_categories"] = _categorical(frame["sex"])
        for field in ("race", "ethnicity", "year_of_birth"):
            s = frame[field].astype("string").str.strip().str.lower()
            out[field + "_missing_unknown_n"] = int((s.isna() | s.isin(["", "unknown", "xxx", "nan"])).sum())
    return out


def preflight(zip_path: Path, sample_rows: int = 10000, max_members: int = 2000) -> dict:
    if sample_rows < 1 or max_members < 1:
        raise ValueError("sample_rows and max_members must be positive")
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)
    with ZipFile(zip_path, "r") as zf:
        members = [m for m in zf.infolist() if not m.is_dir()]
        contents = {m.filename: m for m in members}
        headers = []
        for info in members[:max_members]:
            extension = PurePosixPath(info.filename).suffix.lower()
            fields = safe_member_header(zf, info) if extension in (".csv", ".tsv") else None
            matches = [f for f in (fields or []) if is_encounter_identifier(f)]
            headers.append({
                "member": info.filename,
                "format": extension,
                "uncompressed_bytes": info.file_size,
                "field_names": fields,
                "possible_encounter_fields": matches,
            })
        samples = {}
        for role, name in ROLE_FILES.items():
            if name not in contents:
                samples[role] = {"status": "member_missing", "expected_member": name}
                continue
            info = contents[name]
            header = safe_member_header(zf, info)
            if header is None:
                samples[role] = {"status": "not_csv", "expected_member": name}
                continue
            missing = sorted(REQUIRED[role] - set(header))
            if missing:
                samples[role] = {"status": "missing_required_headers", "missing_fields": missing}
                continue
            columns = list(SAMPLE_FIELDS[role])
            with zf.open(info, "r") as f:
                frame = pd.read_csv(f, usecols=columns, nrows=sample_rows, dtype="string", low_memory=False)
            samples[role] = {"status": "first_rows_checked", "member": name, **sample_summary(role, frame)}
    return {
        "stage": "BOUNDED_ZIP_PREFLIGHT_NOT_FULL_SOURCE_SCAN",
        "archive_member_count": len(members),
        "headers_checked_n": len(headers),
        "all_member_headers": headers,
        "source_preflight": samples,
        "first_n_rows_limit_per_source": sample_rows,
        "all_members_scanned": len(headers) == len(members),
        "ready_for_population_inference": False,
        "limitations": [
            "Only headers and first N rows were read; samples may be sorted and are not representative.",
            "Absence of an encounter field in headers means patient/date linkage requires explicit validation.",
            "No patient identifiers, geographic values or event-level records were exported.",
            "Historical imaging codebook, source cohort definition, date windows and provider approvals remain open.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--sample-rows", type=int, default=10000)
    parser.add_argument("--max-members", type=int, default=2000)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/phase1/zip_preflight.json")
    args = parser.parse_args()
    result = preflight(args.zip, args.sample_rows, args.max_members)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("ZIP preflight summary (first records ONLY):", args.output)
    print("Members inspected:", result["headers_checked_n"])
    for role, part in result["source_preflight"].items():
        print(role, part["status"], part.get("sample_rows_read", 0))
    print("DO NOT use these first-row samples for cohort rates or clinical inference.")


if __name__ == "__main__":
    main()
