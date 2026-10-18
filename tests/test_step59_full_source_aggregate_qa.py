"""Synthetic-only QA for whole-member streaming counters and privacy guards."""
import csv
import io
import json
import stat
import zipfile
from pathlib import Path

import pytest
from scripts import step59_full_source_aggregate_qa as qa


@pytest.fixture
def source(tmp_path):
    tables = {
        "encounter.csv": [
            {"patient_id":"SYN_P1", "encounter_id":"SYN_E1", "type":"IMP", "start_date":"2016-01-01", "end_date":"2016-01-04"},
            {"patient_id":"SYN_P1", "encounter_id":"SYN_E2", "type":"EMER", "start_date":"2017-02-01", "end_date":""},
            {"patient_id":"SYN_P2", "encounter_id":"SYN_E3", "type":"OTHER_PRIVATE", "start_date":"bad-date", "end_date":"bad-date"},
            {"patient_id":"SYN_P3", "encounter_id":"SYN_E4", "type":"IMP", "start_date":"2026-08-01", "end_date":"2026-08-02"},
        ],
        "procedure.csv": [
            {"patient_id":"SYN_P1", "encounter_id":"SYN_E1", "date":"2016-01-02", "code_system":"CPT", "code":"70551"},
            {"patient_id":"SYN_P1", "encounter_id":"SYN_E2", "date":"2017-02-01", "code_system":"SNOMED", "code":"SYN_873"},
            {"patient_id":"SYN_P3", "encounter_id":"SYN_E4", "date":"2026-08-01", "code_system":"CPT", "code":"70471"},
            {"patient_id":"SYN_P2", "encounter_id":"SYN_E3", "date":"", "code_system":"ICD-10-PCS", "code":"SYN_987"},
            {"patient_id":"SYN_P2", "encounter_id":"SYN_E3", "date":"2015-12-31", "code_system":"CPT", "code":"70472"},
        ],
        "diagnosis.csv": [
            {"patient_id":"SYN_P1", "encounter_id":"SYN_E1", "date":"2016-01-02", "code_system":"ICD-10-CM", "code":"I63.9", "principal_diagnosis_indicator":"P"},
            {"patient_id":"SYN_P2", "encounter_id":"SYN_E3", "date":"2017-02-02", "code_system":"ICD-10-CM", "code":"I63.9", "principal_diagnosis_indicator":"S"},
        ]
    }
    archive = tmp_path/"SYNTHETIC.zip"
    files = {}
    manifest = {}
    with zipfile.ZipFile(archive,"w") as z:
        for name,rows in tables.items():
            f = io.StringIO()
            writer = csv.DictWriter(f, fieldnames=qa.FIELDS[name[:-4]], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            blob=f.getvalue().encode("utf-8")
            z.writestr("synthetic/"+name,blob)
            files[name]={"present":True,"headers":list(qa.FIELDS[name[:-4]]),"uncompressed_bytes":len(blob)}
            manifest[name]={"row_count":len(rows)}
    preflight=tmp_path/"pref.json"
    preflight.write_text(json.dumps({"stage":"STEP36_RESEARCH_METADATA_PREFLIGHT", "clinical_rows_read":0,"full_clinical_tables_scanned":False,"files":files,"relevant_manifest_counts":manifest}))
    return archive,preflight,tmp_path


def test_encounter_counts_and_missingness(source):
    z,p,_ = source
    r=qa.inspect(z,"encounter",p,current_year=2026)
    assert r["result"]["rows_scanned"]==4
    assert r["result"]["missing_required_values"]=={"end_date":1}
    assert r["result"]["rows_by_year_bucket_NOT_COVERAGE_VERIFIED"]=={"2016":1,"2017":1,"2026":1,"INVALID":1}
    assert r["result"]["encounter_type_by_year_bucket_NOT_INPATIENT_ADMISSIONS"]=={"2016|IMP":1,"2017|EMER":1,"2026|IMP":1,"INVALID|OTHER_OR_EMPTY":1}
    assert r["HCO_linkage_verified"] is False
    assert r["final_study_end_year_approved"] is False


def test_procedure_only_known_code_groups_and_core_not_patients(source):
    z,p,_=source
    r=qa.inspect(z,"procedure",p,current_year=2026)
    assert r["result"]["rows_scanned"]==5
    assert r["result"]["imaging_code_rows_by_year_NOT_SCANS_OR_PATIENTS"]=={
        "2016|CPT14_CORE_CODE_ROWS":1,"2026|CTA_HEAD_NECK_70471_CANDIDATE":1,
        "BEFORE_2016|CT_PERFUSION_SEPARATE":1
    }
    assert r["result"]["code_system_by_year_bucket_NOT_PERFORMED_PROCEDURES"]=={
        "2016|CPT":1,"2017|SNOMED":1,"2026|CPT":1,"BEFORE_2016|CPT":1,"MISSING|ICD-10-PCS":1
    }
    report=json.dumps(r)
    for prohibited in ("SYN_P", "SYN_E", "SYN_873", "SYN_987", "70551", "I63.9"):
        assert prohibited not in report
    assert r["imaging_completion_verified"] is False


def test_diagnosis_principal_is_a_label_not_validation(source):
    z,p,_=source
    r=qa.inspect(z,"diagnosis",p,current_year=2026)
    assert r["result"]["principal_indicator_by_year_bucket_NOT_VALIDATED"]=={
        "2016|P":1,"2017|OTHER_OR_EMPTY":1
    }


@pytest.mark.parametrize("stage",["patient", "", "procedure.csv", "ALL"])
def test_no_unsupported_full_source_stages(source,stage):
    z,p,_=source
    with pytest.raises(ValueError,match="Stage must"):
        qa.inspect(z,stage,p)


def test_preflight_provenance_and_count_fail_closed(source):
    z,p,_=source
    data=json.loads(p.read_text())
    data["relevant_manifest_counts"]["procedure.csv"]["row_count"]+=1
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="Whole-member row count"):
        qa.inspect(z,"procedure",p)


def test_preflight_source_mutation_is_rejected(source):
    z,p,_=source
    data=json.loads(p.read_text())
    data["files"]["procedure.csv"]["uncompressed_bytes"]+=1
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="Step36 preflight"):
        qa.inspect(z,"procedure",p)


def test_protect_private_output_and_refuse_overwrite(source):
    z,p,root=source
    report=qa.inspect(z,"encounter",p)
    folder=root/"QA_PRIVATE"
    folder.mkdir(mode=0o700)
    target=folder/"test.json"
    qa.write_private(report,target,base=folder)
    assert stat.S_IMODE(target.stat().st_mode)==0o600
    with pytest.raises(FileExistsError):
        qa.write_private(report,target,base=folder)
    with pytest.raises(ValueError,match="dedicated ignored"):
        qa.write_private(report,root/"notprivate.json",base=folder)


def test_dates_are_bounded_and_never_inferred_as_complete():
    assert qa.year_bucket("2014-01-01",2026)=="BEFORE_2016"
    assert qa.year_bucket("2027-01-01",2026)=="AFTER_CURRENT_YEAR"
    assert qa.year_bucket("bad",2026)=="INVALID"
    assert qa.year_bucket("",2026)=="MISSING"
    assert qa.year_bucket("2018-05-17T19:01:00",2026)=="2018"
    assert qa.year_bucket("2026-02-30",2026)=="INVALID"


def test_ack_is_explicit_and_cannot_skip(tmp_path):
    with pytest.raises(SystemExit) as err:
        qa.main(["--zip",str(tmp_path/"fake.zip"),"--stage","procedure","--acknowledge","WRONG"])
    assert err.value.code==2


@pytest.mark.parametrize("text, expected", [
    ("20160101", "2016"),
    ("20171231", "2017"),
    ("20260228", "2026"),
    ("20240229", "2024"),
    ("2018-05-17", "2018"),
    ("2018-05-17T19:01:00", "2018"),
    ("20150101", "BEFORE_2016"),
    ("20270101", "AFTER_CURRENT_YEAR"),
    ("20260230", "INVALID"),
    ("20261301", "INVALID"),
    ("20260001", "INVALID"),
    ("2024ABCD", "INVALID"),
    ("01022018", "INVALID"),
    ("", "MISSING"),
])
def test_unseparated_yyyymmdd_strict_calendar_date(text, expected):
    assert qa.year_bucket(text, current_year=2026) == expected


def test_bounded_probe_formats_without_exact_dates_or_identifiers(source):
    z, preflight, root = source
    assert qa.probe_dates(z, "encounter", max_rows=1000) == {
        "PARSED_CALENDAR_DATE": 3,
        "INVALID": 1,
        "MISSING": 0,
        "BEFORE_2016": 0,
        "AFTER_CURRENT_YEAR": 0,
    }
    assert qa.probe_dates(z, "procedure", max_rows=3)["PARSED_CALENDAR_DATE"] == 3
    assert "SYN_P" not in repr(qa.probe_dates(z, "encounter"))
    with pytest.raises(ValueError, match="bounded row cap"):
        qa.probe_dates(z, "encounter", max_rows=1001)


def test_datefix_v2_source_report_provenance(source):
    z, prior, root = source
    r = qa.inspect(z, "procedure", prior, current_year=2026)
    assert r["date_parser_version"] == "YYYYMMDD_OR_ISO8601_VALIDATED_V2"
    assert r["final_study_end_year_approved"] is False
    assert r["result"]["rows_scanned"] == 5


def test_command_rejects_unversioned_rescan_without_touching_source(tmp_path):
    with pytest.raises(SystemExit) as error:
        qa.main(["--zip", str(tmp_path / "not_found.zip"),
                 "--stage", "encounter", "--acknowledge", qa.ACK])
    assert error.value.code == 2


def test_command_probe_only_does_not_create_report(source, monkeypatch, capsys):
    z, prior, root = source
    # Probe reads bounded synthetic prefix and does not create any private report.
    monkeypatch.setattr(qa, "PRIVATE", root / "NEVER_CREATED")
    qa.main(["--zip", str(z), "--stage", "encounter",
             "--acknowledge", qa.ACK, "--probe-dates"])
    printed = capsys.readouterr().out
    assert "PARSED_CALENDAR_DATE" in printed
    assert "SYN_P1" not in printed
    assert not (root / "NEVER_CREATED").exists()


def test_compact_yyyymmdd_source_rows_group_into_valid_year(tmp_path):
    import json as _json
    z = tmp_path / "SYNTH_COMPACT.zip"
    # Genuine line breaks are required; avoid escaped backslash-n bytes.
    blob = ("\n".join([
        "patient_id,encounter_id,type,start_date,end_date",
        "SYNTH_PERSON_A,SYNTH_ENC_A,IMP,20160101,20160103",
        "SYNTH_PERSON_B,SYNTH_ENC_B,EMER,20201010,20201011",
        "SYNTH_PERSON_C,SYNTH_ENC_C,IMP,20260230,",
    ]) + "\n").encode("utf-8")
    with zipfile.ZipFile(z, "w") as ar:
        ar.writestr("nested/encounter.csv", blob)
    pre = tmp_path / "preflight.json"
    headers = list(qa.FIELDS["encounter"])
    pre.write_text(_json.dumps({
        "stage": "STEP36_RESEARCH_METADATA_PREFLIGHT",
        "clinical_rows_read": 0,
        "full_clinical_tables_scanned": False,
        "files": {"encounter.csv": {
            "present": True, "headers": headers,
            "uncompressed_bytes": len(blob)}},
        "relevant_manifest_counts": {"encounter.csv": {"row_count": 3}},
    }))
    report = qa.inspect(z, "encounter", pre, current_year=2026)
    assert report["result"]["rows_by_year_bucket_NOT_COVERAGE_VERIFIED"] == {
        "2016": 1, "2020": 1, "INVALID": 1}
    assert "SYNTH_PERSON_A" not in repr(report)
