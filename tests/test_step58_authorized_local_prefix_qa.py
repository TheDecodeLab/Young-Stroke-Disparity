"""Step58 local-only bounded clinical-prefix technical checks; all input SYNTHETIC."""
import csv
import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts import step58_authorized_local_prefix_qa as s

TEST_ROWS = {
    "patient.csv": [
        {"patient_id":"SYNTH_P1","sex":"M","race":"Unknown",
         "ethnicity":"","year_of_birth":"1987"},
        {"patient_id":"SYNTH_P2","sex":"F","race":"Unknown",
         "ethnicity":"","year_of_birth":"1993"},
        {"patient_id":"SYNTH_P3","sex":"F","race":"Unknown",
         "ethnicity":"","year_of_birth":"1995"},
    ],
    "encounter.csv": [
        {"patient_id":"SYNTH_P1","encounter_id":"SYNTH_E1",
         "start_date":"2021-03-02","end_date":"2021-03-05","type":"IMP"},
        {"patient_id":"SYNTH_P2","encounter_id":"SYNTH_E2",
         "start_date":"2020-01-01","end_date":"2020-01-02","type":"EMER"},
        {"patient_id":"SYNTH_P3","encounter_id":"SYNTH_E3",
         "start_date":"2026-03-01","end_date":"2026-03-02","type":"EMER"},
    ],
    "diagnosis.csv": [
        {"patient_id":"SYNTH_P1","encounter_id":"SYNTH_E1","date":"2021-03-02",
         "code_system":"ICD-10-CM","code":"SYNTHETIC_ONLY","principal_diagnosis_indicator":"P"},
        {"patient_id":"SYNTH_P2","encounter_id":"SYNTH_E2","date":"INVALID-DATE",
         "code_system":"ICD-10-CM","code":"SYNTHETIC_ONLY","principal_diagnosis_indicator":""},
        {"patient_id":"SYNTH_P3","encounter_id":"SYNTH_E3","date":"2026-03-01",
         "code_system":"ICD-10-CM","code":"SYNTHETIC_ONLY","principal_diagnosis_indicator":"P"},
    ],
    "procedure.csv": [
        {"patient_id":"SYNTH_P1","encounter_id":"SYNTH_E1","date":"2021-03-02",
         "code_system":"CPT","code":"70551"},
        {"patient_id":"SYNTH_P2","encounter_id":"SYNTH_E2","date":"2020-01-01",
         "code_system":"SNOMED","code":"123456"},
        {"patient_id":"SYNTH_P3","encounter_id":"SYNTH_E3","date":"2026-03-01",
         "code_system":"CPT","code":"70496"},
    ],
}


@pytest.fixture()
def fake_local_source():
    private=s.ROOT/"results"/"phase1"/"full_reconstruction_private"
    private.mkdir(parents=True,exist_ok=True,mode=0o700)
    with tempfile.TemporaryDirectory(prefix="step58_fake_",dir=private) as tmp:
        root=Path(tmp)
        zippath=root/"FAKE_ONLY.zip"
        files={}
        with zipfile.ZipFile(zippath,"w") as z:
            for table,rows in TEST_ROWS.items():
                buf=io.StringIO(newline="")
                writer=csv.DictWriter(buf,fieldnames=s.MEMBERS[table],lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
                blob=buf.getvalue().encode("utf-8")
                z.writestr("fakeprefix/"+table,blob)
                files[table]={
                    "present":True,"uncompressed_bytes":len(blob),
                    "headers":list(s.MEMBERS[table]),
                }
        preflight=root/"METADATA_ONLY.json"
        preflight.write_text(json.dumps({
            "stage":"STEP36_RESEARCH_METADATA_PREFLIGHT",
            "clinical_rows_read":0,
            "full_clinical_tables_scanned":False,
            "files":files,
        }))
        yield zippath,preflight,root


def test_bounded_prefix_limits_actual_rows(fake_local_source):
    z,p,_=fake_local_source
    result=s.inspect(z,p,max_rows=2)
    assert result["clinical_rows_inspected_limited_prefix_only"] is True
    assert result["full_clinical_table_scanned"] is False
    assert result["network_wide_estimates_permitted"] is False
    assert result["research_network_end_year_confirmed"] is False
    assert all(v["rows_in_prefix"]==2 for v in result["tables"].values())
    assert result["tables"]["encounter.csv"]["observed_years_in_prefix_NOT_COVERAGE"]==[2020,2021]
    assert result["tables"]["procedure.csv"]["CPT14_code_rows_in_prefix_NOT_CAPTURE_RATE"]==1
    assert result["tables"]["diagnosis.csv"]["unparseable_nonblank_date_counts_in_prefix"]=={"date":1}


def test_extra_third_row_is_not_observed_in_prefix(fake_local_source):
    z,p,_=fake_local_source
    result=s.inspect(z,p,max_rows=2)
    assert 2026 not in result["tables"]["encounter.csv"]["observed_years_in_prefix_NOT_COVERAGE"]
    assert result["tables"]["procedure.csv"]["code_system_counts_in_prefix_NOT_PREVALENCE"]=={
        "CPT":1, "SNOMED":1
    }


def test_no_raw_identifiers_or_codes_reappear_in_any_output(fake_local_source):
    z,p,_=fake_local_source
    result=s.inspect(z,p,max_rows=3)
    serialized=json.dumps(result)
    assert "SYNTH_P" not in serialized
    assert "SYNTH_E" not in serialized
    assert "SYNTHETIC_ONLY" not in serialized
    assert "70551" not in serialized
    assert result["raw_patient_or_encounter_identifiers_in_output"] is False


@pytest.mark.parametrize("bad", [0, 1001, -1, True, "100"])
def test_invalid_or_unbounded_prefix_limit_fails(bad,fake_local_source):
    z,p,_=fake_local_source
    with pytest.raises(ValueError,match="1-1000"):
        s.inspect(z,p,max_rows=bad)


def test_corrupted_metadata_provenance_fails(fake_local_source):
    z,p,_=fake_local_source
    prior=json.loads(p.read_text())
    prior["clinical_rows_read"]=2
    p.write_text(json.dumps(prior))
    with pytest.raises(ValueError,match="metadata-only"):
        s.inspect(z,p)


def test_different_archive_fails_preflight_size_or_header(fake_local_source):
    z,p,_=fake_local_source
    prior=json.loads(p.read_text())
    prior["files"]["procedure.csv"]["uncompressed_bytes"]+=1
    p.write_text(json.dumps(prior))
    with pytest.raises(ValueError,match="signature"):
        s.inspect(z,p)


def test_output_path_outside_private_workspace_refused():
    with pytest.raises(ValueError,match="inside ignored private"):
        s.save_private({"stage":"FAKE_ONLY"},output=Path("/tmp/public.txt"))


def test_private_file_permissions_and_no_overwrite(fake_local_source):
    z,p,root=fake_local_source
    target=root/"PILOT_LOCAL_ONLY.json"
    report=s.inspect(z,p,max_rows=1)
    saved=s.save_private(report,output=target)
    assert saved==target
    assert target.stat().st_mode & 0o077==0
    assert "SYNTH_P" not in target.read_text()
    old=target.read_bytes()
    with pytest.raises(FileExistsError,match="already exists"):
        s.save_private(report,output=target)
    assert target.read_bytes()==old


def test_code_system_and_encounter_type_counters_are_grouped_not_raw(fake_local_source):
    z,p,_=fake_local_source
    result=s.inspect(z,p,max_rows=3)
    assert result["tables"]["encounter.csv"]["encounter_type_counts_in_prefix_NOT_FULL_SOURCE"]=={
        "EMER":2,"IMP":1
    }
    assert result["tables"]["procedure.csv"]["code_system_counts_in_prefix_NOT_PREVALENCE"]=={
        "CPT":2,"SNOMED":1
    }
    assert result["tables"]["patient.csv"]["missing_field_counts_in_prefix"]=={
        "ethnicity":3
    }


def test_no_change_to_step45_clinical_scan_guard():
    old=(s.ROOT/"scripts"/"step45_full_cohort_reconstruction.py").read_text()
    assert "Real clinical scan disabled for superseded Step45 phenotype" in old
    assert s.ACCEPT=="I_CONFIRM_APPROVED_LOCAL_BOUNDED_CLINICAL_QA"
