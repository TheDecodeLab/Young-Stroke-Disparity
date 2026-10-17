"""Step39 synthetic-only tests. Clinical ZIP and patient records are never used."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts.step39_encounter_type_clinical_review import (
    BUNDLE, HEADER, PHASE1, REPORT, WORKSHEET, read_reference, run,
)


@pytest.fixture
def private_sandbox():
    PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step39_synthetic_", dir=PHASE1) as tmp:
        yield Path(tmp)


def as_csv(headers, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def fixtures(folder, unknown=False):
    encounters = as_csv(
        ["encounter_id", "patient_id", "type"],
        [
            {"encounter_id": "SECRET_ENC_" + str(i),
             "patient_id": "SECRET_PATIENT_" + str(i),
             "type": "IMP" if i < 12 else ("MISSING" if unknown else "OTHER")}
            for i in range(20)
        ],
    )
    reference = as_csv(
        ["code_system", "code", "code_description", "path"],
        [
            {"code_system": "Encounter Type", "code": "IMP",
             "code_description": "Inpatient stay", "path": ""},
            {"code_system": "Encounter Type", "code": "OTHER",
             "code_description": "Other type not further classified", "path": ""},
            {"code_system": "CPT", "code": "IMP",
             "code_description": "Not an encounter classification", "path": ""},
        ],
    )
    source = folder / "synthetic.zip"
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("test/encounter.csv", encounters)
        z.writestr("test/standardized_terminology.csv", reference)
    meta36 = {
        "stage": "STEP36_RESEARCH_METADATA_PREFLIGHT",
        "schema_supports_attempted_encounter_linkage": True,
        "files": {"encounter.csv": {"uncompressed_bytes": len(encounters.encode())}},
    }
    p36 = folder / "step36.json"
    b36 = json.dumps(meta36).encode()
    p36.write_bytes(b36)
    meta37 = {
        "stage": "STEP37_RESEARCH_ENCOUNTER_BOUNDED_PILOT",
        "input_step36_sha256": hashlib.sha256(b36).hexdigest(),
    }
    p37 = folder / "step37.json"
    b37 = json.dumps(meta37).encode()
    p37.write_bytes(b37)
    meta38 = {
        "stage": "STEP38_ENCOUNTER_TYPE_REFERENCE_PILOT",
        "input_step37_sha256": hashlib.sha256(b37).hexdigest(),
        "encounter_rows_examined": 20,
        "terminology_rows_examined": 3,
        "encounter_type_reference_rows_found": 2,
        "distinct_encounter_type_values_in_prefix": 2,
    }
    p38 = folder / "step38.json"
    p38.write_text(json.dumps(meta38))
    return source, p36, p37, p38


def test_local_codebook_and_review_zip_separation(private_sandbox):
    source, p36, p37, p38 = fixtures(private_sandbox)
    result = run(source, p36, p37, p38, private_sandbox, 20, 100)
    assert result["distinct_encounter_codes_with_reference"] == 2
    assert result["local_worksheet_reference_rows"] == 2
    assert result["code_definitions_other_than_unambiguous_inpatient_n"] == 1
    assert result["clinician_approval_obtained"] is False
    with (private_sandbox / WORKSHEET).open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert set(rows[0]) == set(HEADER)
    assert sorted(int(r["prefix_record_count_NOT_PREVALENCE"]) for r in rows) == [8, 12]
    assert all(not row["clinician_decision_LEAVE_BLANK"] for row in rows)
    report = (private_sandbox / REPORT).read_text()
    for secret in ("SECRET_PATIENT", "SECRET_ENC", '"IMP"', '"OTHER"', "Inpatient stay"):
        assert secret not in report
    for path in (WORKSHEET, REPORT, BUNDLE):
        assert (private_sandbox / path).stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(private_sandbox / BUNDLE) as z:
        assert z.namelist() == [REPORT]
        assert json.loads(z.read(REPORT)) == result
        assert b"IMP" not in z.read(REPORT)


def test_missing_reference_code_blocks_export(private_sandbox):
    source, p36, p37, p38 = fixtures(private_sandbox, unknown=True)
    with pytest.raises(ValueError, match="Not all observed codes"):
        run(source, p36, p37, p38, private_sandbox, 20, 100)
    assert not (private_sandbox / WORKSHEET).exists()
    assert not (private_sandbox / BUNDLE).exists()


def test_wrong_step37_digest_blocks(private_sandbox):
    source, p36, p37, p38 = fixtures(private_sandbox)
    obj = json.loads(p38.read_text())
    obj["input_step37_sha256"] = "invalid"
    p38.write_text(json.dumps(obj))
    with pytest.raises(ValueError, match="Step38 provenance mismatch"):
        run(source, p36, p37, p38, private_sandbox, 20, 100)


def test_unknown_source_manifest_signature_blocks(private_sandbox):
    source, p36, p37, p38 = fixtures(private_sandbox)
    obj = json.loads(p36.read_text())
    obj["files"]["encounter.csv"]["uncompressed_bytes"] += 1
    b36 = json.dumps(obj).encode()
    p36.write_bytes(b36)
    b37 = json.dumps({
        "stage": "STEP37_RESEARCH_ENCOUNTER_BOUNDED_PILOT",
        "input_step36_sha256": hashlib.sha256(b36).hexdigest(),
    }).encode()
    p37.write_bytes(b37)
    obj38 = json.loads(p38.read_text())
    obj38["input_step37_sha256"] = hashlib.sha256(b37).hexdigest()
    p38.write_text(json.dumps(obj38))
    with pytest.raises(ValueError, match="Source encounter.csv differs"):
        run(source, p36, p37, p38, private_sandbox, 20, 100)


@pytest.mark.parametrize("n,ref", [(0, 100), (200001, 100), (20, 0), (20, 3000001)])
def test_boundaries_blocked(private_sandbox, n, ref):
    source, p36, p37, p38 = fixtures(private_sandbox)
    with pytest.raises(ValueError, match="must be"):
        run(source, p36, p37, p38, private_sandbox, n, ref)


def test_reference_stream_limit_enforced(private_sandbox):
    source, p36, p37, p38 = fixtures(private_sandbox)
    with pytest.raises(ValueError, match="Reference row bound reached"):
        run(source, p36, p37, p38, private_sandbox, 20, 2)
    assert not (private_sandbox / REPORT).exists()


def test_outside_repo_output_rejected(private_sandbox):
    source, p36, p37, p38 = fixtures(private_sandbox)
    with pytest.raises(ValueError, match="results/phase1"):
        run(source, p36, p37, p38, PHASE1.parents[1], 20, 100)


def test_duplicate_reference_labels_are_inspectable_only_locally(private_sandbox):
    source, p36, p37, p38 = fixtures(private_sandbox)
    with zipfile.ZipFile(source) as z:
        labels, scanned, n = read_reference(z, "test/standardized_terminology.csv", {"IMP"}, 100)
    assert labels["IMP"] == {("Inpatient stay", "")}
    assert scanned == 3 and n == 2
