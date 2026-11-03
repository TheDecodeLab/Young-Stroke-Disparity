"""Step50 synthetic-only tests. No Research Network data or clinical rows."""
from __future__ import annotations

import json
import stat
import tempfile
from pathlib import Path

import pytest

from scripts import step50_site_linkage_metadata_check as m


@pytest.fixture
def workspace():
    m.PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step50_synthetic_", dir=m.PHASE1) as temp:
        root = Path(temp)
        yield root, root / "step36_private.json", root / "private_site_review"


def fake_preflight(encounter_headers=None, *, clinical_rows=0):
    return {
        "stage": "STEP36_RESEARCH_METADATA_PREFLIGHT",
        "clinical_rows_read": clinical_rows,
        "full_clinical_tables_scanned": False,
        "schema_supports_attempted_encounter_linkage": True,
        "files": {
            "encounter.csv": {
                "present": True,
                "headers": encounter_headers or [
                    "patient_id", "encounter_id", "start_date",
                    "end_date", "type", "source_id", "hco_id",
                ],
            },
            "patient.csv": {
                "present": True, "headers": ["patient_id", "sex", "race"]
            },
            "diagnosis.csv": {
                "present": True,
                "headers": ["patient_id", "encounter_id", "code", "source_id"],
            },
            "procedure.csv": {
                "present": True,
                "headers": ["patient_id", "encounter_id", "code", "source_id"],
            },
        },
    }


def save_source(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_header_hints_not_hospital_verification(workspace):
    _, src, out = workspace
    save_source(src, fake_preflight())
    expected = src.read_bytes()
    obj = m.prepare(src, out)
    assert src.read_bytes() == expected
    assert obj["clinical_rows_read"] == 0
    assert obj["source_zip_accessed"] is False
    assert obj["actual_hco_id_verified"] is False
    assert obj["source_id_can_be_used_as_site_key"] is False
    assert obj["encounter_possible_hco_or_episode_columns"] == ["hco_id"]
    assert obj["source_id_if_present_remains_unverified"] is True
    assert "source_id" not in obj["encounter_possible_hco_or_episode_columns"]
    assert (out / m.REPORT.name).is_file()
    assert (out / m.REVIEW.name).is_file()
    attestation = json.loads((out / m.REVIEW.name).read_text())
    assert attestation["same_hco_mapping_confirmed"] is False
    assert attestation["patient_id_scope_confirmed"] is False
    assert attestation["verified_same_hco_key_name"] == ""
    assert "patient_id" not in obj["encounter_possible_hco_or_episode_columns"]
    assert out.stat().st_mode & 0o077 == 0
    assert (out / m.REPORT.name).stat().st_mode & 0o077 == 0


def test_only_source_id_present_is_not_site_confirmation(workspace):
    _, src, out = workspace
    p = fake_preflight(["patient_id","encounter_id","type","start_date",
                        "end_date","source_id"])
    save_source(src, p)
    obj = m.prepare(src, out)
    assert obj["encounter_possible_hco_or_episode_columns"] == []
    assert obj["source_id_if_present_remains_unverified"] is True


def test_parent_episode_key_is_only_structural_hint(workspace):
    _, src, out = workspace
    p = fake_preflight(["patient_id","encounter_id","type","start_date",
                        "end_date","parent_encounter_id","facility_id"])
    save_source(src,p)
    obj = m.prepare(src,out)
    assert obj["encounter_possible_hco_or_episode_columns"] == [
        "facility_id", "parent_encounter_id"
    ]
    assert obj["true_ED_IP_episode_linkage_verified"] is False


@pytest.mark.parametrize("broken", [
    ("stage", "INVALID"),
    ("clinical_rows_read", 3),
    ("full_clinical_tables_scanned", True),
])
def test_provenance_rejects_non_structural_source(workspace, broken):
    _, src, out = workspace
    obj = fake_preflight()
    obj[broken[0]] = broken[1]
    save_source(src,obj)
    with pytest.raises(ValueError,match="metadata-only"):
        m.prepare(src,out)
    assert not out.exists()


def test_missing_required_metadata_table_fails(workspace):
    _, src, out = workspace
    p=fake_preflight()
    del p["files"]["encounter.csv"]
    save_source(src,p)
    with pytest.raises(ValueError,match="required table missing"):
        m.prepare(src,out)
    assert not out.exists()


def test_duplicate_header_is_warning_not_verification(workspace):
    _,src,out=workspace
    p=fake_preflight(["patient_id","patient_id","encounter_id","start_date",
                      "end_date","type"])
    save_source(src,p)
    obj=m.prepare(src,out)
    assert "duplicate_header_names_encounter.csv" in obj["warnings"]
    assert obj["actual_hco_id_verified"] is False


def test_preparation_refuses_overwriting_local_annotation(workspace):
    _,src,out=workspace
    save_source(src,fake_preflight())
    m.prepare(src,out)
    original=(out/m.REVIEW.name)
    original.write_text("DO NOT OVERWRITE")
    with pytest.raises(FileExistsError):
        m.prepare(src,out)
    assert original.read_text()=="DO NOT OVERWRITE"


def test_output_rejected_outside_gitignored_private_area(workspace):
    _,src,out=workspace
    save_source(src,fake_preflight())
    with pytest.raises(ValueError,match="results/phase1"):
        m.prepare(src,Path("/tmp/step50_not_allowed"))


def test_missing_key_headers_are_recorded_but_not_invented(workspace):
    _,src,out=workspace
    p=fake_preflight(["patient_id","start_date","end_date","type"])
    p["schema_supports_attempted_encounter_linkage"]=False
    save_source(src,p)
    obj=m.prepare(src,out)
    assert obj["source_step36_structural_preflight_supports_linkage"] is False
    assert obj["table_field_hints"]["encounter.csv"]["encounter_id_present"] is False
    assert obj["true_ED_IP_episode_linkage_verified"] is False


def test_status_contains_no_original_patient_identifiers(workspace):
    _,src,out=workspace
    p=fake_preflight()
    # Construct header-only metadata; no clinical field values anywhere.
    save_source(src,p)
    report=m.prepare(src,out)
    assert "TEST_PATIENT" not in json.dumps(report)
    assert "test_patient_value" not in (out/m.REPORT.name).read_text()
    assert "source_zip_accessed" in report
