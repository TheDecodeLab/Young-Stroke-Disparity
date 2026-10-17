"""Synthetic-only Step37 tests; all generated data stay in gitignored results/phase1/."""
from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts.step37_research_encounter_pilot import (
    PHASE1, REPORT_NAME, ZIP_NAME, REDACTED, coarse_year, private_count,
    run, type_group, output_dir_guard, sample_overlap,
)


@pytest.fixture
def sandbox():
    PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step37_synthetic_", dir=PHASE1) as folder:
        yield Path(folder)


def csv_content(headers, rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def make_source(folder, *, n=40, omit_procedure_code=False):
    source = folder / "synthetic_source.zip"
    headers = {
        "encounter.csv": [
            "encounter_id", "patient_id", "start_date", "end_date", "type", "source_id",
        ],
        "diagnosis.csv": [
            "patient_id", "encounter_id", "code_system", "code", "date",
            "principal_diagnosis_indicator", "source_id",
        ],
        "procedure.csv": [
            "patient_id", "encounter_id", "code_system", "code", "date", "source_id",
        ],
    }
    if omit_procedure_code:
        headers["procedure.csv"].remove("code")
    tables = {}
    for k in range(n):
        eid, pid = "enc_" + str(k), "PRIVATE_PERSON_" + str(k)
        tables.setdefault("encounter.csv", []).append({
            "encounter_id": eid, "patient_id": pid, "start_date": "2018-06-02",
            "end_date": "2018-06-04", "type": "INPATIENT" if k < 25 else "EMERGENCY",
            "source_id": "site_1",
        })
        tables.setdefault("diagnosis.csv", []).append({
            "patient_id": pid, "encounter_id": eid, "code_system": "ICD-10-CM",
            "code": "I63.9", "date": "2018-06-02",
            "principal_diagnosis_indicator": "P", "source_id": "site_1",
        })
        tables.setdefault("procedure.csv", []).append({
            "patient_id": pid, "encounter_id": eid, "code_system": "CPT",
            "code": "70551", "date": "2018-06-03", "source_id": "site_1",
        })
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, rows in tables.items():
            z.writestr("export/" + name, csv_content(headers[name], rows))
    preflight = {
        "stage": "STEP36_RESEARCH_METADATA_PREFLIGHT",
        "schema_supports_attempted_encounter_linkage": True,
        "files": {
            name: {
                "present": True,
                "missing_expected_fields": [],
                "uncompressed_bytes": len(csv_content(headers[name], rows).encode()),
            }
            for name, rows in tables.items()
        },
    }
    prior_path = folder / "step36_synthetic_preflight.json"
    prior_path.write_text(json.dumps(preflight), encoding="utf-8")
    return source, prior_path


def test_pilot_output_is_aggregate_only(sandbox):
    source, prior = make_source(sandbox)
    report = run(source, prior, sandbox, 20)
    assert report["sampling_method"] == "first_n_rows_per_table_NOT_RANDOM"
    assert report["exhaustive_clinical_scan"] is False
    for table in ("encounter.csv", "diagnosis.csv", "procedure.csv"):
        assert report["source_tables"][table]["rows_examined"] == 20
        assert report["source_tables"][table]["max_rows_exhausted_or_table_finished"] is True
    assert report["sample_overlap"]["diagnosis.csv"]["encounter_id_seen_in_encounter_prefix_n"] == 20
    assert report["sample_overlap"]["procedure.csv"]["matching_patient_id_when_observed_n"] == 20
    assert report["sample_overlap"]["procedure.csv"]["agreeing_nonblank_source_id_when_observed_n"] == 20
    assert report["source_tables"]["procedure.csv"]["restricted_characteristic_counts"]["CPT_14_catalog_code"] == 20
    payload = (sandbox / REPORT_NAME).read_text(encoding="utf-8")
    assert "PRIVATE_PERSON" not in payload
    assert "enc_19" not in payload
    assert str(source) not in payload
    assert (sandbox / REPORT_NAME).stat().st_mode & 0o077 == 0
    assert (sandbox / ZIP_NAME).stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(sandbox / ZIP_NAME) as z:
        assert z.namelist() == [REPORT_NAME]
        assert json.loads(z.read(REPORT_NAME)) == report


def test_empty_date_and_type_are_not_inferred():
    assert coarse_year("2018-09-02") == "2018_2019"
    assert coarse_year("2019-02-30") == "unparseable"
    assert coarse_year("not-a-date") == "unparseable"
    assert coarse_year("") == "missing"
    assert type_group("INPATIENT") == "inpatient_label_candidate"
    assert type_group("Emergency Department") == "emergency_label_candidate"
    assert type_group("unmapped opaque value") == "unclassified"


def test_small_counts_suppressed():
    assert private_count(0) == 0
    assert private_count(1) == REDACTED
    assert private_count(10) == REDACTED
    assert private_count(11) == 11


def test_preflight_signature_mismatch_rejected(sandbox):
    source, prior = make_source(sandbox)
    bad = json.loads(prior.read_text())
    bad["files"]["encounter.csv"]["uncompressed_bytes"] += 1
    prior.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="ZIP signature mismatch"):
        run(source, prior, sandbox, 10)
    assert not (sandbox / REPORT_NAME).exists()


def test_missing_required_header_rejected(sandbox):
    source, prior = make_source(sandbox, omit_procedure_code=True)
    with pytest.raises(ValueError, match="Missing required headers"):
        run(source, prior, sandbox, 10)
    assert not (sandbox / REPORT_NAME).exists()


def test_outside_output_directory_rejected(sandbox):
    with pytest.raises(ValueError, match="results/phase1"):
        output_dir_guard(sandbox.parents[2] / "outside")
    source, prior = make_source(sandbox)
    with pytest.raises(ValueError, match="results/phase1"):
        run(source, prior, sandbox.parents[2], 10)


@pytest.mark.parametrize("limit", [0, -1, 200001])
def test_unbounded_sample_rejected(sandbox, limit):
    source, prior = make_source(sandbox)
    with pytest.raises(ValueError, match="1..200000"):
        run(source, prior, sandbox, limit)


def test_short_source_finishes_without_full_scan_claim(sandbox):
    source, prior = make_source(sandbox, n=13)
    report = run(source, prior, sandbox, 20)
    assert report["source_tables"]["encounter.csv"]["rows_examined"] == 13
    assert report["source_tables"]["encounter.csv"]["max_rows_exhausted_or_table_finished"] is False
    assert report["exhaustive_clinical_scan"] is False


def test_source_id_disagreement_is_reported_without_exposing_identifiers():
    rows = [{"encounter_id": "SECRET_E", "patient_id": "SECRET_P", "source_id": "site_wrong"}]
    result = sample_overlap(rows, {"SECRET_E": ("SECRET_P", "site_right")})
    assert result["matching_patient_id_when_observed_n"] == REDACTED
    assert result["differing_nonblank_source_id_when_observed_n"] == REDACTED
    assert "SECRET_" not in json.dumps(result)
