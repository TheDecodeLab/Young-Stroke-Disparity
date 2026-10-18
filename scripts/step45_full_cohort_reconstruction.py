#!/usr/bin/env python3
"""Step45 guarded FULL Research Network cohort reconstruction (NOT auto-run).

Two parallel co-primary age cohorts: uniform 18-50, historical men 18-52
and women 18-54. Uses a bounded-memory, disk-backed private SQLite stage.
One completed whole-file pass per source table. No prefix-based claims.
ALL generated files are within the cloned repo's ignored results/phase1/.
The real full scan is blocked without explicit documented approvals.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import zipfile
import zlib
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "results" / "phase1" / "full_reconstruction_private"
STEP36 = ROOT / "results" / "phase1" / "step36_research_metadata_preflight.json"
CONFIG = PRIVATE / "approvals_LOCAL_ONLY.json"
CODEBOOK = PRIVATE / "imaging_codebook_APPROVED_LOCAL_ONLY.csv"
DB = PRIVATE / "reconstruction_STAGE_PRIVATE.sqlite"
REPORT = PRIVATE / "co_primary_cohort_aggregates_LOCAL_ONLY.json"
STAGES = ("diagnosis", "encounter", "patient", "index", "procedure", "report")
TABLE_MAP = {
    "diagnosis": "diagnosis.csv", "encounter": "encounter.csv",
    "patient": "patient.csv", "procedure": "procedure.csv",
}
FIELDS = {
    "diagnosis.csv": {"patient_id", "encounter_id", "code_system", "code", "date",
                      "principal_diagnosis_indicator"},
    "encounter.csv": {"patient_id", "encounter_id", "start_date", "end_date", "type"},
    "patient.csv": {"patient_id", "sex", "race", "ethnicity", "year_of_birth"},
    "procedure.csv": {"patient_id", "encounter_id", "date", "code_system", "code"},
}
DEFINITIONS = ("uniform_18_50", "original_sex_specific_18_52_54")
CATEGORIES = ("MRI_BRAIN", "CTA_HEAD", "CTA_NECK", "MRA_HEAD", "MRA_NECK", "CT_HEAD")
APPROVAL_KEYS = (
    "institutional_data_use_approved", "encrypted_local_storage_confirmed",
    "principal_diagnosis_indicator_approved", "inpatient_IMP_definition_approved",
    "source_id_key_scope_approved", "age_definitions_and_YOB_policy_approved",
    "imaging_codebook_and_procedure_status_approved",
    "aggregate_disclosure_plan_approved",
)
CONFIRM = "I_ACKNOWLEDGE_FULL_TRINETX_CLINICAL_SCAN"
SCHEMA = """
CREATE TABLE IF NOT EXISTS stages(stage TEXT PRIMARY KEY, records_read INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS run_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS candidate(
  patient_id TEXT NOT NULL, encounter_id TEXT NOT NULL, dxday TEXT NOT NULL,
  PRIMARY KEY(patient_id, encounter_id, dxday));
CREATE INDEX IF NOT EXISTS candidate_eid ON candidate(encounter_id);
CREATE TABLE IF NOT EXISTS admission(
  patient_id TEXT NOT NULL, encounter_id TEXT NOT NULL,
  start_day TEXT NOT NULL, end_day TEXT,
  PRIMARY KEY(patient_id, encounter_id));
CREATE INDEX IF NOT EXISTS admission_patient_start ON admission(patient_id,start_day,encounter_id);
CREATE TABLE IF NOT EXISTS person(
  patient_id TEXT PRIMARY KEY, sex TEXT NOT NULL, race TEXT NOT NULL,
  ethnicity TEXT NOT NULL, yob INTEGER);
CREATE TABLE IF NOT EXISTS index_encounter(
  cohort TEXT NOT NULL, patient_id TEXT NOT NULL, encounter_id TEXT NOT NULL,
  start_day TEXT NOT NULL, end_day TEXT, sex TEXT NOT NULL, race TEXT NOT NULL,
  age_min INTEGER, age_max INTEGER, PRIMARY KEY(cohort,patient_id));
CREATE INDEX IF NOT EXISTS index_key ON index_encounter(patient_id,encounter_id);
CREATE TABLE IF NOT EXISTS observed(
  cohort TEXT NOT NULL, patient_id TEXT NOT NULL, category TEXT NOT NULL,
  window TEXT NOT NULL, PRIMARY KEY(cohort,patient_id,category,window));
CREATE TABLE IF NOT EXISTS age_audit(
  cohort TEXT NOT NULL, patient_id TEXT NOT NULL, status TEXT NOT NULL,
  PRIMARY KEY(cohort, patient_id));
"""


def private_path(path: Path) -> Path:
    base = ROOT.resolve() / "results" / "phase1"
    private_base = base / "full_reconstruction_private"
    if (ROOT / "results" / "phase1").resolve() != base:
        raise ValueError("results/phase1 cannot be a symlink escape")
    resolved = path.expanduser().resolve()
    if resolved != private_base and private_base not in resolved.parents:
        raise ValueError("Generated inputs/outputs must stay inside cloned repo results/phase1/full_reconstruction_private/")
    return resolved


def prepare_private():
    folder = private_path(PRIVATE)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.stat().st_mode & 0o077:
        raise PermissionError("Private reconstruction directory must be mode 0700; chmod 700 results/phase1/full_reconstruction_private")
    return folder


def safe_save(path, obj):
    path = private_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix=".step45_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.write("\n")
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def approval_template():
    return {
        **{k: False for k in APPROVAL_KEYS},
        "reviewer_name": "",
        "review_date": "",
        "authorization_reference": "",
        "confirmed_principal_flag": "P",
        "confirmed_inpatient_type": "IMP",
        "co_primary_age_definitions": list(DEFINITIONS),
        "age_boundary_policy": "definitely_eligible_only",
        "source_linkage_policy": "patient_id_plus_encounter_id",
        "index_policy": "earliest_eligible_hospitalization_per_patient",
    }


def init_templates():
    prepare_private()
    if CONFIG.exists() or CODEBOOK.exists():
        raise FileExistsError("Local approval/codebook template exists; cannot replace any review decisions")
    safe_save(CONFIG, approval_template())
    codebook_header = "code_system,code,category,record_meaning,reviewer,review_date\n"
    fd = os.open(CODEBOOK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(codebook_header)
    print("Templates created INSIDE ignored private reconstruction folder; all approvals remain FALSE.")
    print("No full dataset scan or patient records read.")


def parse_day(value):
    text = (value or "").strip()
    try:
        if re.fullmatch(r"\d{8}", text):
            return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return date.fromisoformat(text)
    except ValueError:
        return None
    return None


def norm_sex(value):
    text = (value or "").strip().lower()
    if text in ("m", "male"): return "male"
    if text in ("f", "female"): return "female"
    return "unknown_or_other"


def norm_race(value):
    text = (value or "").strip().lower()
    if not text or text in ("unknown", "not recorded", "unspecified", "null", "not reported"):
        return "missing"
    if "white" in text: return "white"
    if "black" in text or "african american" in text: return "black"
    if "asian" in text: return "asian"
    return "other_or_unmapped"


def age_class(event_date, yob, sex, definition):
    """Exact DOB not available: require the ENTIRE possible age interval in bounds."""
    if not isinstance(yob, int) or not 1900 <= yob <= event_date.year:
        return "unknown"
    low, high = event_date.year - yob - 1, event_date.year - yob
    max_age = 50 if definition == DEFINITIONS[0] else (
        52 if sex == "male" else 54 if sex == "female" else None
    )
    if max_age is None: return "unknown"
    if low >= 18 and high <= max_age: return "eligible"
    if high < 18 or low > max_age: return "ineligible"
    return "boundary_uncertain"


def members_and_preflight(z, preflight):
    if (preflight.get("stage") != "STEP36_RESEARCH_METADATA_PREFLIGHT" or
            preflight.get("schema_supports_attempted_encounter_linkage") is not True):
        raise ValueError("Valid Step36 structural preflight required")
    found = {}
    for info in z.infolist():
        if info.is_dir(): continue
        base = info.filename.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if base in FIELDS:
            if base in found: raise ValueError("Duplicate source table basename")
            found[base] = info.filename
    if set(found) != set(FIELDS):
        raise ValueError("All four clinical source tables required")
    for base, member in found.items():
        expected = preflight.get("files", {}).get(base, {})
        if not expected.get("present") or expected.get("uncompressed_bytes") != z.getinfo(member).file_size:
            raise ValueError("Step36 source ZIP size signature mismatch")
    return found


def validate_approvals(path, codebook):
    status = json.loads(private_path(path).read_text(encoding="utf-8"))
    if any(status.get(k) is not True for k in APPROVAL_KEYS):
        raise PermissionError("Full source execution BLOCKED: required documented approvals missing")
    if not all(isinstance(status.get(k), str) and status[k].strip()
               for k in ("reviewer_name", "review_date", "authorization_reference")):
        raise PermissionError("Explicit clinical/data-steward reviewer and authorization required")
    required_values = {
        "confirmed_principal_flag": "P",
        "confirmed_inpatient_type": "IMP",
        "co_primary_age_definitions": list(DEFINITIONS),
        "age_boundary_policy": "definitely_eligible_only",
        "source_linkage_policy": "patient_id_plus_encounter_id",
        "index_policy": "earliest_eligible_hospitalization_per_patient",
    }
    if any(status.get(k) != v for k,v in required_values.items()):
        raise PermissionError("Approval file policy mismatches frozen reconstruction design")
    code_map = {}
    with private_path(codebook).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        needed = {"code_system", "code", "category", "record_meaning", "reviewer", "review_date"}
        if not needed.issubset(reader.fieldnames or ()): raise ValueError("Codebook schema incomplete")
        for row in reader:
            key = ((row["code_system"] or "").strip().upper(), (row["code"] or "").strip().upper())
            category = (row["category"] or "").strip().upper()
            if (not all(key) or category not in CATEGORIES or
                    (row["record_meaning"] or "").strip().lower() != "performed" or
                    not (row["reviewer"] or "").strip() or not (row["review_date"] or "").strip()):
                raise PermissionError("Unapproved or ambiguous imaging codebook row")
            if key in code_map and code_map[key] != category:
                raise ValueError("Contradictory modality assignment for same system/code")
            code_map[key] = category
    if not code_map: raise PermissionError("An explicitly approved, nonempty imaging codebook is required")
    return code_map


def rows_of(z, member, expected_headers):
    with z.open(member) as binary, io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not expected_headers.issubset(reader.fieldnames or ()):
            raise ValueError("Source table missing expected fields")
        yield from reader


def db_open(path):
    path = private_path(path)
    # SQLite's working files must stay in our private repository workspace.
    os.environ["SQLITE_TMPDIR"] = str(path.parent)
    conn = sqlite3.connect(str(path), timeout=120)
    os.chmod(path, 0o600)
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.executescript(SCHEMA)
    return conn


def completed(db, stage):
    return db.execute("SELECT records_read FROM stages WHERE stage=?", (stage,)).fetchone()


def ensure_previous(db, stage):
    index = STAGES.index(stage)
    if index and not completed(db, STAGES[index-1]):
        raise RuntimeError("Previous stage incomplete: " + STAGES[index-1])


class FixedBloom:
    """Fixed 64 MiB membership prefilter; false positives possible, not negatives.

    SQLite remains the final authority for patient+encounter matching.
    """
    def __init__(self):
        self.bits = bytearray(64 * 1024 * 1024)
        self.size = len(self.bits) * 8

    def _positions(self, value):
        b = value.encode("utf-8")
        h1 = zlib.crc32(b) % self.size
        h2 = zlib.adler32(b) % self.size
        return h1, (h1 + h2 + 1) % self.size

    def add(self, value):
        for pos in self._positions(value):
            self.bits[pos >> 3] |= 1 << (pos & 7)

    def contains(self, value):
        return all(self.bits[pos >> 3] & (1 << (pos & 7))
                   for pos in self._positions(value))


def candidate_encounter_bloom(db):
    pref = FixedBloom()
    for (eid,) in db.execute("SELECT DISTINCT encounter_id FROM candidate"):
        pref.add(eid)
    return pref


def staged_scan(z, members, db, stage, codebook, expected_rows):
    """Stage uses a fresh table and marks success ONLY after source EOF.

    Interrupted stages are discarded/restarted, never treated as complete.
    """
    table_name = {"diagnosis":"candidate", "encounter":"admission",
                  "patient":"person", "procedure":"observed"}[stage]
    with db:
        db.execute("DELETE FROM " + table_name)
    source_name = TABLE_MAP[stage]
    scanned = 0
    inserted = 0
    lookup_prefilter = candidate_encounter_bloom(db) if stage == "encounter" else None
    with db:
        for row in rows_of(z, members[source_name], FIELDS[source_name]):
            scanned += 1
            if scanned % 10000 == 0:
                # Only completed full-file passes receive a stage marker.
                # A failed pass is cleared and restarted at the next attempt.
                db.commit()
            pid = (row.get("patient_id") or "").strip()
            eid = (row.get("encounter_id") or "").strip()
            if stage == "diagnosis":
                day = parse_day(row.get("date"))
                code = (row.get("code") or "").strip().upper()
                if (pid and eid and day and day.year in (2018,2019)
                        and (row.get("code_system") or "").strip().upper() == "ICD-10-CM"
                        and re.fullmatch(r"I63(?:\.[A-Z0-9]+)?", code)
                        and (row.get("principal_diagnosis_indicator") or "").strip().upper() == "P"):
                    db.execute("INSERT OR IGNORE INTO candidate VALUES (?,?,?)",
                               (pid, eid, day.isoformat()))
                    inserted += 1
            elif stage == "encounter":
                if (not pid or not eid or
                        not lookup_prefilter.contains(eid)):
                    continue
                if not db.execute(
                    "SELECT 1 FROM candidate WHERE patient_id=? AND encounter_id=? LIMIT 1",
                    (pid,eid)).fetchone():
                    continue
                if (row.get("type") or "").strip().upper() != "IMP":
                    continue
                begin = parse_day(row.get("start_date"))
                end = parse_day(row.get("end_date"))
                if begin is None or begin.year not in (2018, 2019):
                    continue
                if end is not None and end < begin:
                    raise ValueError("Encounter end precedes start in candidate keyset")
                if not db.execute(
                    "SELECT 1 FROM candidate WHERE patient_id=? AND encounter_id=? AND dxday>=? AND dxday<=? LIMIT 1",
                    (pid,eid,(begin-timedelta(days=1)).isoformat(),
                     ((end or begin)+timedelta(days=1)).isoformat())).fetchone():
                    continue
                existing = db.execute(
                    "SELECT start_day,end_day FROM admission WHERE patient_id=? AND encounter_id=?",
                    (pid,eid)).fetchone()
                if existing and existing != (begin.isoformat(),end.isoformat() if end else None):
                    raise ValueError("Conflicting repeated encounter records")
                other = db.execute(
                    "SELECT 1 FROM admission WHERE encounter_id=? AND patient_id<>? LIMIT 1",
                    (eid,pid)).fetchone()
                if other: raise ValueError("Encounter ID reused for different patients in matched candidate set")
                db.execute("INSERT OR IGNORE INTO admission VALUES (?,?,?,?)",
                           (pid,eid,begin.isoformat(),end.isoformat() if end else None))
                inserted += 1
            elif stage == "patient":
                if not pid or not db.execute(
                    "SELECT 1 FROM admission WHERE patient_id=? LIMIT 1", (pid,)).fetchone():
                    continue
                sex = norm_sex(row.get("sex"))
                race = norm_race(row.get("race"))
                ethnicity = (row.get("ethnicity") or "").strip().lower() or "missing"
                yob = (row.get("year_of_birth") or "").strip()
                year = int(yob) if re.fullmatch(r"\d{4}",yob) else None
                existing = db.execute("SELECT sex,race,ethnicity,yob FROM person WHERE patient_id=?",(pid,)).fetchone()
                if existing and existing != (sex,race,ethnicity,year):
                    raise ValueError("Conflicting patient demographic records")
                db.execute("INSERT OR IGNORE INTO person VALUES (?,?,?,?,?)",
                           (pid,sex,race,ethnicity,year))
                inserted += 1
            else:
                if not pid or not eid: continue
                key = ((row.get("code_system") or "").strip().upper(),
                       (row.get("code") or "").strip().upper())
                category = codebook.get(key)
                if not category: continue
                day = parse_day(row.get("date"))
                if day is None: continue
                candidate_indexes = db.execute(
                    "SELECT cohort,start_day,end_day FROM index_encounter WHERE patient_id=? AND encounter_id=?",
                    (pid,eid)).fetchall()
                for cohort, start_txt, end_txt in candidate_indexes:
                    start = date.fromisoformat(start_txt)
                    finish = date.fromisoformat(end_txt) if end_txt else start
                    if end_txt and start <= day <= finish:
                        db.execute("INSERT OR IGNORE INTO observed VALUES (?,?,?,?)"
                                   (cohort,pid,category,"within_stay"))
                        inserted += 1
                    if abs((day-start).days) <= 7:
                        db.execute("INSERT OR IGNORE INTO observed VALUES (?,?,?,?)",
                                   (cohort,pid,category,"same_encounter_pm7"))
        if expected_rows is None or scanned != expected_rows:
            raise ValueError(
                "Full source pass row count does not match approved Step36 manifest; stage not marked complete"
            )
        db.execute("INSERT INTO stages(stage,records_read) VALUES (?,?)", (stage,scanned))
    return {"stage":stage, "records_read":scanned, "candidate_hits_in_memory_or_disk_private":inserted}


def make_index(db):
    scanned = 0
    counters = Counter()
    with db:
        db.execute("DELETE FROM index_encounter")
        db.execute("DELETE FROM age_audit")
        query = """SELECT a.patient_id,a.encounter_id,a.start_day,a.end_day,
                          p.sex,p.race,p.yob FROM admission a
                   LEFT JOIN person p ON p.patient_id=a.patient_id
                   ORDER BY a.patient_id,a.start_day,a.encounter_id"""
        for pid,eid,start_txt,end_txt,sex,race,yob in db.execute(query):
            scanned += 1
            if not sex:
                counters["missing_person"] += 1
                continue
            for cohort in DEFINITIONS:
                status = age_class(date.fromisoformat(start_txt),yob,sex,cohort)
                counters[cohort+"_"+status+"_admission_candidates"] += 1
                # Distinct-patient quality status: eligible > boundary > unknown > ineligible.
                # Do not count one person multiple times due to recurrent admissions.
                priority = {"ineligible":0,"unknown":1,"boundary_uncertain":2,"eligible":3}
                old = db.execute(
                    "SELECT status FROM age_audit WHERE cohort=? AND patient_id=?",
                    (cohort,pid)).fetchone()
                if not old or priority[status] > priority[old[0]]:
                    db.execute(
                        "INSERT OR REPLACE INTO age_audit VALUES (?,?,?)",
                        (cohort,pid,status))
                if status != "eligible": continue
                db.execute("INSERT OR IGNORE INTO index_encounter VALUES (?,?,?,?,?,?,?,?,?)",
                           (cohort,pid,eid,start_txt,end_txt,sex,race,
                            date.fromisoformat(start_txt).year-yob-1,
                            date.fromisoformat(start_txt).year-yob))
        db.execute("INSERT INTO stages(stage,records_read) VALUES (?,?)", ("index",scanned))
    return {"index_candidate_admissions_examined":scanned, "age_quality_counts_private":dict(counters)}


def suppress(n, successes=None):
    """Safeguard numerator and complementary failure counts (not cross-margin proof)."""
    if n == 0: return 0
    if n < 11: return "suppressed"
    if successes is None: return n
    return "suppressed" if (0 < successes < 11 or 0 < n-successes < 11) else successes


def aggregate_report(db):
    """Private descriptive strata only; cross-stratum disclosure NOT approved."""
    measures = {
        "MRI_BRAIN": ("MRI_BRAIN",),
        "CTA_HEAD": ("CTA_HEAD",),
        "CTA_NECK": ("CTA_NECK",),
        "MRA_HEAD": ("MRA_HEAD",),
        "MRA_NECK": ("MRA_NECK",),
        "any_CTA_head_neck": ("CTA_HEAD", "CTA_NECK"),
        "any_MRA_head_neck": ("MRA_HEAD", "MRA_NECK"),
        "any_vascular_CTA_or_MRA": ("CTA_HEAD","CTA_NECK","MRA_HEAD","MRA_NECK"),
        "any_MRI_or_vascular": ("MRI_BRAIN","CTA_HEAD","CTA_NECK","MRA_HEAD","MRA_NECK"),
    }
    outcome_sql = """SELECT COUNT(DISTINCT i.patient_id)
       FROM index_encounter i WHERE i.cohort=? {filter}
       AND EXISTS (
           SELECT 1 FROM observed o WHERE o.cohort=i.cohort
           AND o.patient_id=i.patient_id AND o.window='within_stay'
           AND o.category IN ({categories})
       )"""
    result = {}
    for cohort in DEFINITIONS:
        cohorts = {}
        for segment in ("overall", "sex", "race"):
            if segment == "overall":
                group_sql = "SELECT 'all',COUNT(*) FROM index_encounter WHERE cohort=?"
            else:
                group_sql = ("SELECT "+segment+",COUNT(*) FROM index_encounter "
                             "WHERE cohort=? GROUP BY "+segment)
            strata = {}
            for group, n in db.execute(group_sql,(cohort,)).fetchall():
                filt = "" if segment == "overall" else "AND i."+segment+"=?"
                args = (cohort,) if segment == "overall" else (cohort,group)
                entry = {"denominator_n":suppress(n)}
                count_by_measure={}
                for name,categories in measures.items():
                    placeholders = ",".join("?" for _ in categories)
                    query=outcome_sql.format(filter=filt,categories=placeholders)
                    count=db.execute(query,args+categories).fetchone()[0]
                    count_by_measure[name]=count
                    entry["recorded_"+name+"_within_stay_n"]=suppress(n,count)
                no_advanced = n - count_by_measure["any_MRI_or_vascular"]
                entry["no_recorded_MRI_or_vascular_within_stay_n"]=suppress(n,no_advanced)
                strata[group]=entry
            cohorts[segment]=strata
        result[cohort]=cohorts
    return result

def make_report(db, approvals, codebook_path):
    counts = {stage: n for stage,n in db.execute("SELECT stage,records_read FROM stages")}
    if any(stage not in counts for stage in STAGES[:-1]):
        raise RuntimeError("All source passes and index required before report")
    result = {
        "stage": "STEP45_PRIVATE_FULL_SOURCE_RECONSTRUCTION",
        "co_primary_age_definitions": list(DEFINITIONS),
        "full_source_table_passes_completed": True,
        "source_rows_read_by_stage": counts,
        "imaging_definition": "reviewer-approved recorded performed-code within-stay only",
        "cohort_population": "imaging-independent principal I63 + approved inpatient encounter",
        "codebook_sha256": hashlib.sha256(private_path(codebook_path).read_bytes()).hexdigest(),
        "approval_reference_is_private_and_not_exported": True,
        "age_exactness": "YOB-only conservative definitely-eligible policy",
        "diagnostic_reports_are_private_and_not_approved_for_external_disclosure": True,
        "needs_clinical_interpretation_and_disclosure_review": True,
        "co_primary_aggregates_LOCAL_ONLY": aggregate_report(db),
        "age_boundary_quality_distinct_people_LOCAL_ONLY": {
            cohort: {
                status: suppress(n)
                for status,n in db.execute(
                    "SELECT status,COUNT(*) FROM age_audit WHERE cohort=? GROUP BY status",
                    (cohort,)).fetchall()
            }
            for cohort in DEFINITIONS
        },
        "overlap_people_in_both_primary_cohorts_n": suppress(
            db.execute(
                "SELECT COUNT(*) FROM index_encounter a JOIN index_encounter b "
                "ON a.patient_id=b.patient_id "
                "WHERE a.cohort=? AND b.cohort=?", DEFINITIONS
            ).fetchone()[0]
        ),
        "missing_end_date_in_eligible_indexes_n": {
            cohort: suppress(db.execute(
                "SELECT COUNT(*) FROM index_encounter WHERE cohort=? AND end_day IS NULL",
                (cohort,)).fetchone()[0])
            for cohort in DEFINITIONS
        },
    }
    safe_save(REPORT,result)
    with db:
        db.execute("INSERT INTO stages(stage,records_read) VALUES (?,?)",("report",0))
    return result


def plan(source, preflight_file):
    prior = json.loads(preflight_file.read_text(encoding="utf-8"))
    with zipfile.ZipFile(source) as z:
        members_and_preflight(z, prior)
    print("PLAN ONLY: no clinical table rows read, no database opened.")
    print("Co-primary cohorts:", ", ".join(DEFINITIONS))
    print("Complete source scan sequence: diagnosis -> encounter -> patient -> index -> procedure -> report")
    print("Requires local approval JSON, reviewed performed-imaging codebook, private disk and explicit execute flags.")
    print("Approximate private staging free space required: 16 GiB minimum; actual usage depends on qualifying encounters.")
    print("The full scan was NOT started.")


def run_stage(source, stage, approvals, codebook, preflight, min_free_bytes=16*(1024**3)):
    folder = prepare_private()
    if shutil.disk_usage(folder).free < min_free_bytes:
        raise OSError("Insufficient free space for private stages")
    codes = validate_approvals(approvals, codebook)
    prior = json.loads(preflight.read_text(encoding="utf-8"))
    with zipfile.ZipFile(source) as z:
        members = members_and_preflight(z, prior)
        db = db_open(DB)
        try:
            source_signature = [
                [name, z.getinfo(members[name]).file_size, z.getinfo(members[name]).CRC]
                for name in sorted(members)
            ]
            fingerprint = hashlib.sha256(json.dumps({
                "source_signature": source_signature,
                "preflight_sha256": hashlib.sha256(preflight.read_bytes()).hexdigest(),
                "approvals_sha256": hashlib.sha256(private_path(approvals).read_bytes()).hexdigest(),
                "codebook_sha256": hashlib.sha256(private_path(codebook).read_bytes()).hexdigest(),
                "age_definitions": DEFINITIONS,
            }, sort_keys=True).encode()).hexdigest()
            prior = db.execute("SELECT value FROM run_meta WHERE key='frozen_inputs'").fetchone()
            if prior and prior[0] != fingerprint:
                raise RuntimeError("Frozen source, approvals, preflight, codebook or age policy changed: start a separately reviewed private run")
            if not prior:
                with db:
                    db.execute("INSERT INTO run_meta VALUES ('frozen_inputs',?)", (fingerprint,))
            if completed(db,stage):
                print("Stage already complete; refusing to rerun/duplicate:",stage)
                return
            ensure_previous(db,stage)
            if stage in TABLE_MAP:
                source_name = TABLE_MAP[stage]
                expected_rows = prior.get("relevant_manifest_counts", {}).get(
                    source_name, {}).get("row_count")
                if not isinstance(expected_rows, int) or expected_rows < 0:
                    raise ValueError("Step36 manifest row count must be known before full scan")
                outcome = staged_scan(z,members,db,stage,codes,expected_rows)
            elif stage=="index":
                outcome = make_index(db)
            else:
                outcome = make_report(db,approvals,codebook)
            # No identifiers in stdout; only stage counters, which remain local.
            print("Completed private stage:",stage)
            print("Output remains within:", folder)
            return outcome
        finally:
            db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, help="Source Research Network ZIP; remains outside cloned repo")
    parser.add_argument("--step36", type=Path, default=STEP36)
    parser.add_argument("--init-templates", action="store_true")
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--execute-full-scan", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--approvals", type=Path, default=CONFIG)
    parser.add_argument("--codebook", type=Path, default=CODEBOOK)
    args = parser.parse_args()
    if args.init_templates:
        if args.stage or args.execute_full_scan: parser.error("--init-templates cannot execute a scan")
        init_templates()
        return
    if not args.zip: parser.error("--zip required for plan or execution")
    if not args.stage:
        if args.execute_full_scan: parser.error("--stage required for full scan")
        plan(args.zip,args.step36)
        return
    if not args.execute_full_scan or args.confirm != CONFIRM:
        parser.error("Full scan blocked: --execute-full-scan and exact --confirm phrase both required")
    if not args.zip.is_file(): parser.error("Source ZIP unavailable")
    if args.zip.resolve() == DB.resolve(): parser.error("Input and SQLite DB must differ")
    run_stage(args.zip,args.stage,args.approvals,args.codebook,args.step36)


if __name__ == "__main__":
    main()
