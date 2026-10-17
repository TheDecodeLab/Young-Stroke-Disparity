"""Step 32: read-only subgroup *recording diagnostics*, NOT disparities.

Uses the completed age-eligible and expanded procedure-index SQLite DBs.
No original TriNetX ZIP member is rescanned. The report contains only
broad aggregate code-recording counts (no identifiers, models, or p-values).
Automatically withholds a whole dimension if any nonzero count or
nested/window difference is <11. ALL output requires independent
cross-report disclosure review before release.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import stat

try:
    from scripts.step28_imaging_extract import (
        ROOT, TARGET, STUDY_COHORT, LITERATURE_CODEBOOK, codebook,
        complete_db,
    )
except ModuleNotFoundError:
    from step28_imaging_extract import (
        ROOT, TARGET, STUDY_COHORT, LITERATURE_CODEBOOK, codebook,
        complete_db,
    )

COHORT_DB = "demographics/step19_age_cohort.sqlite"
WINDOWS = (0, 1, 3, 7)
CT, MRI, CTA_H, MRA_H, CTA_N, MRA_N = (1, 2, 4, 8, 16, 32)
HEAD = CT | MRI | CTA_H | MRA_H
WIDE = HEAD | CTA_N | MRA_N
ANATOMY_BIT = {
    ("CT", "head"): CT,
    ("MRI", "brain"): MRI,
    ("CTA", "head"): CTA_H,
    ("MRA", "head"): MRA_H,
    ("CTA", "neck"): CTA_N,
    ("MRA", "neck"): MRA_N,
}


def require(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError("Step 32 integrity failure: " + label)


def age_group(n: int) -> str:
    return "19-29" if n <= 29 else ("30-39" if n <= 39 else "40-50")


def build_flags(cohort_rows: list[tuple], events: list[tuple],
                code_rows: list[dict]) -> tuple[dict, dict]:
    """Private patient IDs occur ONLY in memory, not returned reports."""
    ids = {}
    for pid, day, sex, age in cohort_rows:
        require(pid and isinstance(pid, str) and len(day) == 8,
                "invalid cohort patient/index")
        require(pid not in ids, "duplicate eligible person")
        require(sex in ("Female", "Male") and isinstance(age, int)
                and 19 <= age <= 50, "cohort sex/age mismatch")
        datetime.strptime(day, "%Y%m%d")
        require(day[:4] in ("2018", "2019"), "unexpected index year")
        ids[pid] = (day, sex, age)
    require(ids, "empty eligible index")
    mapping = {}
    for item in code_rows:
        require(item["clinical_review"] == "evidence_reviewed",
                "unreviewed code")
        key = (item["code_system"].upper(), item["code"].upper())
        bit = ANATOMY_BIT.get((item["modality"].upper(), item["anatomy"].lower()))
        require(bit is not None and key not in mapping, "invalid codebook map")
        mapping[key] = bit
    flags = {pid: {w: 0 for w in WINDOWS} for pid in ids}
    seen = set()
    for pid, modality, system, code, procedure_date, offset in events:
        require(pid in ids, "event outside eligible cohort")
        key = (system.upper(), code.upper())
        bit = mapping.get(key)
        require(bit is not None, "unknown procedure code")
        require(bit in (
            (CT, MRI, CTA_H, CTA_N) if modality in ("CT", "MRI", "CTA")
            else (MRA_H, MRA_N)
        ), "event modality mapping disagreement")
        require(abs(int(offset)) <= 7, "event outside extraction window")
        date = datetime.strptime(procedure_date, "%Y%m%d")
        index_date = datetime.strptime(ids[pid][0], "%Y%m%d")
        require((date - index_date).days == int(offset),
                "event offset/date mismatch")
        rowid = (pid, system, code, procedure_date)
        require(rowid not in seen, "duplicate code-specific event")
        seen.add(rowid)
        for w in WINDOWS:
            if abs(int(offset)) <= w:
                flags[pid][w] |= bit
    return ids, flags


def _summary_for(people: list[str], flags: dict) -> dict:
    n = len(people)
    out = {"denominator": n}
    for w in WINDOWS:
        vals = [flags[p][w] for p in people]
        out[str(w)] = {
            "any_head_n": sum(bool(v & HEAD) for v in vals),
            "any_head_or_neck_n": sum(bool(v & WIDE) for v in vals),
            "head_CT_n": sum(bool(v & CT) for v in vals),
            "brain_MRI_n": sum(bool(v & MRI) for v in vals),
            "head_CTA_n": sum(bool(v & CTA_H) for v in vals),
            "head_MRA_n": sum(bool(v & MRA_H) for v in vals),
            "head_or_neck_CTA_n": sum(bool(v & (CTA_H | CTA_N)) for v in vals),
            "head_or_neck_MRA_n": sum(bool(v & (MRA_H | MRA_N)) for v in vals),
            "none_head_or_neck_n": sum(v == 0 for v in vals),
        }
    return out


def unsafe_dimension(rows: list[dict]) -> bool:
    """Protect smaller nonzero counts and complementary differences."""
    keys = list(rows[0]["windows"]["0"]) if rows else []
    for row in rows:
        n = row["denominator"]
        if 0 < n < 11:
            return True
        prev = None
        for w in WINDOWS:
            d = row["windows"][str(w)]
            values = [*d.values(), n - d["any_head_n"]]
            if any(0 < val < 11 for val in values):
                return True
            if prev is not None and any(
                0 < abs(d[k] - prev[k]) < 11 for k in keys
            ):
                return True
            # Head-only vs combined figures can reconstruct rare neck-only groups.
            diffs = (
                d["any_head_or_neck_n"] - d["any_head_n"],
                d["head_or_neck_CTA_n"] - d["head_CTA_n"],
                d["head_or_neck_MRA_n"] - d["head_MRA_n"],
            )
            if any(0 < v < 11 for v in diffs):
                return True
            prev = d
    return False


def summarize(ids: dict, flags: dict) -> dict:
    groups = {"index_year": defaultdict(list),
              "recorded_sex": defaultdict(list),
              "age_band": defaultdict(list)}
    for pid, (day, sex, age) in ids.items():
        groups["index_year"][day[:4]].append(pid)
        groups["recorded_sex"][sex].append(pid)
        groups["age_band"][age_group(age)].append(pid)
    result = {}
    for dim, stratified in groups.items():
        rows = []
        for label, people in sorted(stratified.items()):
            info = _summary_for(people, flags)
            rows.append({"stratum": label, "denominator": info["denominator"],
                         "windows": {w: info[w] for w in map(str, WINDOWS)}})
        # If any stratum could be reconstructable, suppress the WHOLE dimension.
        if unsafe_dimension(rows):
            result[dim] = {"suppressed": True}
        else:
            result[dim] = {"suppressed": False, "strata": rows}
    return result


def run(private_dir: Path, expansion_report: Path) -> dict:
    private = private_dir.expanduser().resolve()
    require(private.is_dir() and ROOT.resolve() not in private.parents
            and private != ROOT.resolve(), "private databases must be outside Git")
    require((stat.S_IMODE(private.stat().st_mode) & 0o077) == 0,
            "private folder must have owner-only permissions")
    cohort_file = private / COHORT_DB
    imaging_file = private / TARGET
    complete_db(cohort_file)
    complete_db(imaging_file)
    with sqlite3.connect(cohort_file.as_uri() + "?mode=ro", uri=True) as c:
        config = dict(c.execute("SELECT key,value FROM scan_state"))
        require((config.get("min_age"), config.get("max_age")) == ("19", "50"),
                "cohort age definition")
        cohort = list(c.execute(
            "SELECT patient_id,index_date,sex,age FROM eligible"))
    with sqlite3.connect(imaging_file.as_uri() + "?mode=ro", uri=True) as c:
        status = dict(c.execute("SELECT key,value FROM scan_state"))
        events = list(c.execute(
            "SELECT patient_id,modality,code_system,code,procedure_date,offset_days "
            "FROM event"))
    mapping, digest, catalog = codebook(LITERATURE_CODEBOOK)
    r = json.loads(expansion_report.read_text(encoding="utf-8"))
    require(r.get("stage") == "STEP28_EXPANDED_CODE_EXTRACTION_TEMPORAL_PROXY"
            and r.get("review_basis") ==
            "published_evidence_only_no_independent_clinician_signoff"
            and r.get("encounter_validated") is False, "Step30 source provenance")
    require(status.get("codebook_sha256") == digest
            == r.get("approved_codebook_sha256"), "codebook digest mismatch")
    require(status.get("archive_members_sha256")
            and status["archive_members_sha256"] != "", "missing source signature")
    require(status.get("source_rows_scanned") ==
            str(r.get("source_procedure_rows_scanned")),
            "procedure source count mismatch")
    require(len(events) == r.get("matched_code_specific_patient_days"),
            "code-specific event count mismatch")
    ids, flags = build_flags(cohort, events, catalog)
    n = len(ids)
    require(n == r.get("eligible_diagnosis_first_patients"),
            "eligible denominator mismatch")
    for w in WINDOWS:
        expected = r["anatomic_profiles_by_window"][str(w)]
        require(not expected.get("suppressed"), "reference summary suppressed")
        total = _summary_for(list(ids), flags)["PLACEHOLDER"] if False else None
        actual = _summary_for(list(ids), flags)[str(w)]
        head = expected["head_only_primary"]
        wide = expected["head_plus_neck_sensitivity"]
        require(actual["any_head_n"] == n - head["None of four"]
                and actual["any_head_or_neck_n"] ==
                n - wide["None of four"], "any code count disagrees")
        for field, name in (
            ("head_CT_n", "CT"), ("brain_MRI_n", "MRI"),
            ("head_CTA_n", "CTA"), ("head_MRA_n", "MRA")
        ):
            require(actual[field] == head[name], "head-only " + name)
        require(actual["head_or_neck_CTA_n"] == wide["CTA"]
                and actual["head_or_neck_MRA_n"] == wide["MRA"],
                "head+neck CTA/MRA disagreement")
        require(actual["none_head_or_neck_n"] == wide["None of four"],
                "unmatched code count disagrees")
    return {
        "stage": "STEP32_READ_ONLY_RECORDING_HETEROGENEITY_QC",
        "recording_scope": "2018-2019 earliest principal I63 patient/date",
        "private_sqlite_source_verified": True,
        "original_zip_rows_scanned": 0,
        "private_patient_level_rows_exported": 0,
        "denominator": n,
        "code_specific_event_rows_read": len(events),
        "groupwise_coding_diagnostics": summarize(ids, flags),
        "small_cell_control": (
            "Whole broad dimension suppressed when any nonzero cell, "
            "window difference or nested-anatomy difference is <11; "
            "cross-report complementary disclosure remains possible."
        ),
        "clinical_inference_allowed": False,
        "race_ethnicity_inference_allowed": False,
        "publication_disclosure_review_required": True,
        "warning": (
            "These are patterns of recorded CPT codes near I63 diagnoses, "
            "not performed imaging, stroke admissions or disparities in access."
        )
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--compare-expanded", type=Path, required=True)
    p.add_argument("--output", type=Path, default=ROOT /
                   "results/phase1/step32_recording_heterogeneity_qc.json")
    args = p.parse_args()
    report = run(args.private_dir, args.compare_expanded)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("Read-only broad-stratum code-recording audit:", args.output)
    print("Source ZIP rows scanned: 0. No inferential disparity claims.")


if __name__ == "__main__":
    main()
