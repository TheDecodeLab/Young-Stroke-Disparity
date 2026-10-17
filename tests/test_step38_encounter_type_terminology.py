"""Synthetic-only Step38 tests, with temporary files under ignored results/phase1/."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts.step38_encounter_type_terminology import (
    PHASE1, REPORT, REVIEW, SMALL, category_from_text, normalize_type, run,
    secure_directory, summarise, suppress,
)


@pytest.fixture
def sandbox():
    PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step38_synthetic_", dir=PHASE1) as name:
        yield Path(name)


def csv_text(headers, data):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(data)
    return buf.getvalue()


def synthetic_inputs(folder):
    encounters = csv_text(
        ["encounter_id", "patient_id", "type", "start_date"],
        [{"encounter_id": "SENSITIVE_ENC_" + str(k),
          "patient_id": "SENSITIVE_PERSON_" + str(k),
          "type": ["IMP", "AMB", "EMER", "UNKNOWN"][k % 4],
          "start_date": "20200102"} for k in range(60)]
    )
    terms = csv_text(
        ["code_system", "code", "code_description", "path", "unit"],
        [
            {"code_system": "Encounter Type", "code": "IMP", "code_description": "Inpatient encounter", "path": "", "unit": ""},
            {"code_system": "Encounter Type", "code": "AMB", "code_description": "Ambulatory encounter", "path": "", "unit": ""},
            {"code_system": "Encounter Type", "code": "EMER", "code_description": "Emergency department", "path": "", "unit": ""},
            {"code_system": "CPT", "code": "AMB", "code_description": "Not an encounter type", "path": "", "unit": ""},
        ]
    )
    source = folder / "synthetic_source.zip"
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("export/encounter.csv", encounters)
        z.writestr("export/standardized_terminology.csv", terms)
    prior36 = {
        "stage": "STEP36_RESEARCH_METADATA_PREFLIGHT",
        "schema_supports_attempted_encounter_linkage": True,
        "files": {"encounter.csv": {"uncompressed_bytes": len(encounters.encode())}},
    }
    p36 = folder / "synthetic_step36.json"
    blob = (json.dumps(prior36) + "\n").encode()
    p36.write_bytes(blob)
    prior37 = {
        "stage": "STEP37_RESEARCH_ENCOUNTER_BOUNDED_PILOT",
        "input_step36_sha256": hashlib.sha256(blob).hexdigest(),
        "source_tables": {"encounter.csv": {"rows_examined": 60}},
    }
    p37 = folder / "synthetic_step37.json"
    p37.write_text(json.dumps(prior37), encoding="utf-8")
    return source, p36, p37


def test_source_ontology_decoding_and_private_outputs(sandbox):
    source, p36, p37 = synthetic_inputs(sandbox)
    report = run(source, p36, p37, sandbox, max_encounters=60, max_terms=1000)
    assert report["encounter_rows_examined"] == 60
    assert report["terminology_rows_examined"] == 4
    assert report["encounter_type_reference_rows_found"] == 3
    assert report["encounter_category_candidate_counts"]["terminology_inpatient_candidate"] == 15
    assert report["encounter_category_candidate_counts"]["terminology_outpatient_candidate"] == 15
    assert report["encounter_category_candidate_counts"]["terminology_emergency_candidate"] == 15
    assert report["encounter_category_candidate_counts"]["unclassified"] == 15
    assert report["encounter_type_lookup_coverage"]["mapped_to_encounter_type_terminology"] == 45
    assert report["raw_encounter_type_values_exported"] is False
    assert report["ready_for_disparity_analysis"] is False
    content = (sandbox / REPORT).read_text()
    for forbidden in ("SENSITIVE", '"IMP"', '"AMB"', '"EMER"'):
        assert forbidden not in content
    assert (sandbox / REPORT).stat().st_mode & 0o077 == 0
    assert (sandbox / REVIEW).stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(sandbox / REVIEW) as z:
        assert z.namelist() == [REPORT]
        assert json.loads(z.read(REPORT)) == report


def test_unmapped_and_ambiguous_categories():
    c, coverage = summarise({"UNKNOWN1": 20, "IMP": 30, "BAD": 11},
                            {"IMP": {"inpatient_candidate"}, "BAD": {"inpatient_candidate", "outpatient_candidate"}})
    assert c["unclassified"] == 20
    assert c["terminology_inpatient_candidate"] == 30
    assert c["ambiguous_reference_mapping"] == 11
    assert coverage["mapped_to_encounter_type_terminology"] == 41


def test_characteristic_missingness_and_suppression():
    groups, coverage = summarise({"": 5, "MISSED": 2}, {})
    assert groups["missing_type"] == SMALL
    assert groups["unclassified"] == SMALL
    assert coverage["missing_type"] == SMALL
    assert coverage["no_reference_match"] == SMALL
    assert suppress(0) == 0 and suppress(10) == SMALL and suppress(11) == 11


def test_category_classification_does_not_treat_codes_as_admissions():
    assert normalize_type("  imp ") == "IMP"
    assert category_from_text("IMP") == "unclassified"
    assert category_from_text("Inpatient encounter") == "inpatient_candidate"
    assert category_from_text("Ambulatory encounter") == "outpatient_candidate"
    assert category_from_text("emergency inpatient") == "mixed_candidate"


def test_stale_preflight_rejected(sandbox):
    source, p36, p37 = synthetic_inputs(sandbox)
    prior = json.loads(p37.read_text())
    prior["input_step36_sha256"] = "wrong"
    p37.write_text(json.dumps(prior))
    with pytest.raises(ValueError, match="do not match Step36"):
        run(source, p36, p37, sandbox, max_encounters=60, max_terms=1000)
    assert not (sandbox / REPORT).exists()


def test_terminology_scan_cap_rejected(sandbox):
    source, p36, p37 = synthetic_inputs(sandbox)
    with pytest.raises(ValueError, match="Terminology scan cap reached"):
        run(source, p36, p37, sandbox, max_encounters=60, max_terms=3)
    assert not (sandbox / REPORT).exists()


def test_nonmatching_encounter_count_rejected(sandbox):
    source, p36, p37 = synthetic_inputs(sandbox)
    with pytest.raises(ValueError, match="Encounter prefix count differs"):
        run(source, p36, p37, sandbox, max_encounters=20, max_terms=1000)


def test_output_directory_outside_repo_rejected(sandbox):
    with pytest.raises(ValueError, match="results/phase1"):
        secure_directory(PHASE1.parents[1])
    source, p36, p37 = synthetic_inputs(sandbox)
    with pytest.raises(ValueError, match="results/phase1"):
        run(source, p36, p37, PHASE1.parents[1], 60, 1000)


@pytest.mark.parametrize("rows,terms", [(0, 100), (200001, 100), (60, 0), (60, 3000001)])
def test_limit_validation(sandbox, rows, terms):
    source, p36, p37 = synthetic_inputs(sandbox)
    with pytest.raises(ValueError, match="must be in"):
        run(source, p36, p37, sandbox, max_encounters=rows, max_terms=terms)
