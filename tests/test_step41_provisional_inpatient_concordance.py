"""Synthetic only Step41 tests; all generated files under repo results/phase1/."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts.step41_provisional_inpatient_concordance import (
    PHASE1, REPORT, REVIEW_ZIP, candidate_inpatient_codes, parse_date, run,
)


@pytest.fixture
def sandbox():
    PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step41_synthetic_", dir=PHASE1) as folder:
        yield Path(folder)


def encode_csv(fields, rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def synthetic_inputs(folder, bad_patient=False, skip_inpatient=False):
    records = {"encounter.csv": [], "diagnosis.csv": [], "procedure.csv": []}
    for n in range(50):
        eid, pid = f"SENSITIVE_ENC_{n}", f"SENSITIVE_PAT_{n}"
        care = "TEST_IP" if n < 40 else "TEST_AMB"
        records["encounter.csv"].append({
            "encounter_id": eid, "patient_id": pid, "start_date": "20180701",
            "end_date": "20180704", "type": care,
        })
        records["diagnosis.csv"].append({
            "patient_id": pid, "encounter_id": eid, "code_system": "ICD-10-CM",
            "code": "I63.9" if n < 40 else "E11.9", "date": "20180701",
            "principal_diagnosis_indicator": "P",
        })
        records["procedure.csv"].append({
            "patient_id": "OTHER_PATIENT" if bad_patient and n == 0 else pid,
            "encounter_id": eid, "code_system": "CPT", "code": "70551",
            "date": "20180702",
        })
    headers = {
        "encounter.csv": ["encounter_id", "patient_id", "start_date", "end_date", "type"],
        "diagnosis.csv": [
            "patient_id", "encounter_id", "code_system", "code", "date",
            "principal_diagnosis_indicator",
        ],
        "procedure.csv": ["patient_id", "encounter_id", "code_system", "code", "date"],
    }
    source = folder / "synthetic_clinical.zip"
    files = {}
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, rows in records.items():
            blob = encode_csv(headers[name], rows)
            z.writestr("test/" + name, blob)
            files[name] = {
                "present": True,
                "uncompressed_bytes": len(blob.encode()),
                "missing_expected_fields": [],
            }
    step36 = folder / "step36_synthetic.json"
    raw36 = json.dumps({
        "stage": "STEP36_RESEARCH_METADATA_PREFLIGHT",
        "schema_supports_attempted_encounter_linkage": True,
        "files": files,
    }).encode()
    step36.write_bytes(raw36)
    step37 = folder / "step37_synthetic.json"
    raw37 = json.dumps({
        "stage": "STEP37_RESEARCH_ENCOUNTER_BOUNDED_PILOT",
        "input_step36_sha256": hashlib.sha256(raw36).hexdigest(),
        "max_rows_per_clinical_table": 50,
    }).encode()
    step37.write_bytes(raw37)
    worksheet = folder / "private_worksheet_synthetic.csv"
    with worksheet.open("w", newline="") as f:
        w = csv.DictWriter(
            f, ["encounter_type_code", "reference_description",
                "lexical_candidate_NOT_APPROVED"]
        )
        w.writeheader()
        w.writerows([
            {
                "encounter_type_code": "TEST_IP",
                "reference_description": "Visit: Inpatient Encounter",
                "lexical_candidate_NOT_APPROVED": (
                    "unclassified" if skip_inpatient else "inpatient_candidate"
                ),
            },
            {
                "encounter_type_code": "TEST_AMB",
                "reference_description": "Visit: Ambulatory",
                "lexical_candidate_NOT_APPROVED": "outpatient_candidate",
            },
        ])
    return source, step36, step37, worksheet


def test_prefix_match_and_only_aggregate_report(sandbox):
    source, step36, step37, worksheet = synthetic_inputs(sandbox)
    result = run(source, step36, step37, worksheet, sandbox, 50)
    counts = result["technical_prefix_counts"]
    assert counts["distinct_candidate_inpatient_encounter_ids_n"] == 40
    assert counts["linked_diagnosis_event_rows_with_matching_patient_n"] == 40
    assert counts["linked_procedure_event_rows_with_matching_patient_n"] == 40
    assert counts["I63_diagnosis_event_rows_n"] == 40
    assert counts["CPT14_procedure_event_rows_n"] == 40
    assert counts["both_I63_and_CPT14_in_same_sampled_encounter_encounters_n"] == 40
    assert result["candidate_definition_clinically_approved"] is False
    assert result["ready_for_disparity_model"] is False
    assert result["inpatient_episode_validated"] is False
    content = (sandbox / REPORT).read_text()
    for secret in ("SENSITIVE_", "TEST_IP", "TEST_AMB", "70551", "I63.9"):
        assert secret not in content
    for name in (REPORT, REVIEW_ZIP):
        assert (sandbox / name).stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(sandbox / REVIEW_ZIP) as z:
        assert z.namelist() == [REPORT]
        assert json.loads(z.read(REPORT)) == result


def test_nonmatching_patient_is_never_treated_as_imaging_match(sandbox):
    source, s36, s37, worksheet = synthetic_inputs(sandbox, bad_patient=True)
    out = run(source, s36, s37, worksheet, sandbox, 50)
    c = out["technical_prefix_counts"]
    assert c["matched_prefix_events_with_different_patient_id_n"] == "suppressed_1_to_10"
    assert c["CPT14_procedure_event_rows_n"] == 39
    assert c["both_I63_and_CPT14_in_same_sampled_encounter_encounters_n"] == 39


def test_invalid_or_ambiguous_dates_remain_missing():
    assert parse_date("20180701").isoformat() == "2018-07-01"
    assert parse_date("2018-07-01").isoformat() == "2018-07-01"
    assert parse_date("2018/07/01").isoformat() == "2018-07-01"
    assert parse_date("07/01/2018") is None
    assert parse_date("2018-02-30") is None
    assert parse_date("") is None


def test_unreviewed_private_dictionary_is_not_automatically_approved(sandbox):
    source, s36, s37, worksheet = synthetic_inputs(sandbox)
    codes = candidate_inpatient_codes(worksheet)
    assert codes == {"TEST_IP"}
    report = run(source, s36, s37, worksheet, sandbox, 50)
    assert report["candidate_definition_clinically_approved"] is False


def test_missing_inpatient_candidate_blocks_run(sandbox):
    source, s36, s37, worksheet = synthetic_inputs(sandbox, skip_inpatient=True)
    with pytest.raises(ValueError, match="No unambiguous provisional inpatient"):
        run(source, s36, s37, worksheet, sandbox, 50)
    assert not (sandbox / REPORT).exists()


def test_lineage_mismatch_blocks_run(sandbox):
    source, s36, s37, worksheet = synthetic_inputs(sandbox)
    s37.write_text(json.dumps({
        "stage": "STEP37_RESEARCH_ENCOUNTER_BOUNDED_PILOT",
        "input_step36_sha256": "wrong", "max_rows_per_clinical_table": 50,
    }))
    with pytest.raises(ValueError, match="does not match Step36"):
        run(source, s36, s37, worksheet, sandbox, 50)


def test_sample_bounds_and_prefix_consistency(sandbox):
    source, s36, s37, worksheet = synthetic_inputs(sandbox)
    with pytest.raises(ValueError, match="match Step37"):
        run(source, s36, s37, worksheet, sandbox, 40)
    with pytest.raises(ValueError, match="1..200000"):
        run(source, s36, s37, worksheet, sandbox, 0)


def test_private_outputs_never_leave_repo(sandbox):
    source, s36, s37, worksheet = synthetic_inputs(sandbox)
    with pytest.raises(ValueError, match="results/phase1"):
        run(source, s36, s37, worksheet, PHASE1.parents[1], 50)
