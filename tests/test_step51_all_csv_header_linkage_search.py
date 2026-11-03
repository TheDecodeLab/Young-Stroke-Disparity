"""Step51 synthetic-only tests for bounded ZIP CSV header inspection."""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts import step51_all_csv_header_linkage_search as m


HEADERS = {
    "patient.csv": "patient_id,sex,race,ethnicity,year_of_birth\n",
    "encounter.csv": "patient_id,encounter_id,start_date,end_date,type,source_id\n",
    "diagnosis.csv": "patient_id,encounter_id,code_system,code,date,principal_diagnosis_indicator,source_id\n",
    "procedure.csv": "patient_id,encounter_id,code_system,code,date,source_id\n",
    "episode_links.csv": "episode_id,parent_encounter_id,facility_id,source_id\n",
}
FAKE_ROW = "SYNTHETIC_PATIENT_ROW_MUST_NOT_BE_READ,1234,ABCD\n"


@pytest.fixture
def fake_metadata(tmp_path):
    m.PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step51_synthetic_",dir=m.PHASE1) as temp:
        home=Path(temp)
        zip_path=tmp_path / "research_synthetic.zip"
        preflight_path=home / "step36_research_metadata_preflight.json"
        def build(members=None, *, add_patient_rows=True):
            members = dict(HEADERS if members is None else members)
            with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_STORED) as z:
                for filename,header in members.items():
                    z.writestr("synthetic/"+filename,
                               header + (FAKE_ROW if add_patient_rows else ""))
            prior={
                "stage":"STEP36_RESEARCH_METADATA_PREFLIGHT",
                "clinical_rows_read":0,
                "full_clinical_tables_scanned":False,
                "schema_supports_attempted_encounter_linkage":True,
                "files": {
                    name: {
                        "present":True,
                        "headers":next(__import__("csv").reader([members[name].strip()])),
                        "uncompressed_bytes":len(
                            (members[name]+(FAKE_ROW if add_patient_rows else "")).encode()
                        ),
                    }
                    for name in ("patient.csv","encounter.csv","diagnosis.csv","procedure.csv")
                },
            }
            preflight_path.write_text(json.dumps(prior))
            return zip_path,preflight_path,home
        yield build


def test_only_field_names_and_not_synthetic_clinical_values(fake_metadata):
    src,step36,_=fake_metadata()
    result=m.inspect_headers(src,step36)
    assert result["clinical_rows_read"]==0
    assert result["zip_member_bodies_scanned"] is False
    assert result["file_values_read"] is False
    assert result["csv_headers_examined"]==5
    assert result["zip_core_metadata_signature_reconciled"] is True
    assert result["site_identity_verified"] is False
    assert result["episode_linkage_verified"] is False
    assert "SYNTHETIC_PATIENT_ROW_MUST_NOT_BE_READ" not in json.dumps(result)
    assert not any("SYNTHETIC_PATIENT" in x for x in result["table_header_column_counts"])


def test_other_table_parent_episode_identifier_is_found(fake_metadata):
    src,step36,_=fake_metadata()
    result=m.inspect_headers(src,step36)
    candidate=next(x for x in result["tables_with_candidate_identifier_field_names"]
                   if x["table_basename"]=="episode_links.csv")
    cols={c["column_name"] for c in candidate["columns"]}
    assert {"episode_id","parent_encounter_id","facility_id","source_id"} <= cols
    assert all("NOT_VALIDATED" in c["hint_NOT_VALIDATED"]
               or "NOT_SITE_VALIDATED" in c["hint_NOT_VALIDATED"]
               for c in candidate["columns"])


def test_only_source_id_does_not_become_verified_HCO(fake_metadata):
    base={name:header for name,header in HEADERS.items() if name!="episode_links.csv"}
    src,step36,_=fake_metadata(base)
    result=m.inspect_headers(src,step36)
    assert result["source_id_is_verified_hco_key"] is False
    assert result["site_identity_verified"] is False
    assert not any(
        c["hint_NOT_VALIDATED"].startswith("possible_hco")
        for item in result["tables_with_candidate_identifier_field_names"]
        for c in item["columns"]
    )


def test_preflight_clinical_scan_not_accepted(fake_metadata):
    src,step36,_=fake_metadata()
    obj=json.loads(step36.read_text())
    obj["clinical_rows_read"]=1
    step36.write_text(json.dumps(obj))
    with pytest.raises(ValueError,match="metadata-only"):
        m.inspect_headers(src,step36)


def test_zip_signature_mismatch_blocks(fake_metadata):
    src,step36,_=fake_metadata()
    obj=json.loads(step36.read_text())
    obj["files"]["encounter.csv"]["uncompressed_bytes"]+=1
    step36.write_text(json.dumps(obj))
    with pytest.raises(ValueError,match="signature"):
        m.inspect_headers(src,step36)


def test_core_header_mismatch_blocks(fake_metadata):
    src,step36,_=fake_metadata()
    obj=json.loads(step36.read_text())
    obj["files"]["encounter.csv"]["headers"].append("missing_extra_column")
    step36.write_text(json.dumps(obj))
    with pytest.raises(ValueError,match="core header"):
        m.inspect_headers(src,step36)


def test_duplicate_zip_table_basename_blocked(fake_metadata):
    src,step36,_=fake_metadata()
    with zipfile.ZipFile(src,"a") as z:
        z.writestr("duplicated/encounter.csv",HEADERS["encounter.csv"])
    with pytest.raises(ValueError,match="Duplicate"):
        m.inspect_headers(src,step36)


def test_long_header_never_reads_an_extra_row(fake_metadata):
    members=dict(HEADERS)
    members["episode_links.csv"]="X"*140000+"\n"
    src,step36,_=fake_metadata(members)
    with pytest.raises(ValueError,match="safe header limit"):
        m.inspect_headers(src,step36)


def test_blank_header_never_reads_first_data_row(fake_metadata):
    members=dict(HEADERS)
    members["episode_links.csv"]="\n"
    src,step36,_=fake_metadata(members)
    with pytest.raises(ValueError,match="Invalid/empty"):
        m.inspect_headers(src,step36)


def test_fixed_output_folder_and_no_overwriting(fake_metadata,monkeypatch):
    src,step36,home=fake_metadata()
    report=m.inspect_headers(src,step36)
    private=home/"private"
    monkeypatch.setattr(m,"PRIVATE",private)
    monkeypatch.setattr(m,"OUTPUT",private/"step51_all_csv_header_linkage_hints_LOCAL_ONLY.json")
    path=m.save_private(report)
    assert path.parent==private
    assert path.stat().st_mode & 0o077 == 0
    assert private.stat().st_mode & 0o077 == 0
    text=path.read_text()
    with pytest.raises(FileExistsError):
        m.save_private(report)
    assert path.read_text()==text


def test_output_outside_private_area_rejected(fake_metadata):
    with pytest.raises(ValueError):
        m.save_private({},destination=Path("/tmp/not_allowed_step51.csv"))


@pytest.mark.parametrize("name,kind",[
    ("hco_id","possible_hco_OR_episode_key_NOT_VALIDATED"),
    ("source_id","generic_source_OR_location_NOT_SITE_VALIDATED"),
    ("admission_group_key","name_suggests_hco_OR_episode_REQUIRES_STEWARD_REVIEW"),
    ("parent_encounter_identifier","possible_parent_encounter_REQUIRES_STEWARD_REVIEW"),
    ("encounter_id",None),
    ("patient_id",None),
])
def test_identifier_names_are_hints_only(name,kind):
    assert m.field_hint(name)==kind
