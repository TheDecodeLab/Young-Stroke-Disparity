"""Step62 end-to-end tests use entirely fabricated patient/encounter records."""
import csv
import json
import sqlite3
import stat
import zipfile
from pathlib import Path

import pytest

from scripts import step62_checkpointed_cohort as s


@pytest.fixture
def fake(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "ROOT", tmp_path)
    folder = tmp_path / "results/phase1/full_reconstruction_private/step62_test"
    archive = tmp_path / "SYNTH_STROKE_ONLY.zip"
    files = {
        "diagnosis": [
            ["A","AIP","ICD-10-CM","I63.9","20200105","P"],
            ["A","AIP","ICD-10-CM","I63.9","20200105",""],
            ["B","BIP","ICD-10-CM","I63.9","20210202","P"],
            ["C","CIP","ICD-10-CM","I63.5","20200110","P"],
            ["E","EIP","ICD-10-CM","I63","20240301",""],
            ["F","F1","ICD-10-CM","I63.1","20220105","P"],
            ["F","F2","ICD-10-CM","I63.1","20220105","P"],
            ["A","AED","ICD-10-CM","I63.9","20200104",""],
            ["A","WRONG","ICD-9-CM","I63.9","20200104","P"],
            ["A","RET","ICD-10-CM","H34.1","20200104","P"],
            ["A","NODOT","ICD-10-CM","I639","20200104","P"],
        ],
        "encounter": [
            ["A","AIP","20200104","20200108","IMP"],
            ["A","AED","20200103","20200105","EMER"],
            ["B","BIP","20210202","20210203","IMP"],
            ["C","CIP","20200110","20200111","IMP"],
            ["E","EIP","20240301","20240305","IMP"],
            ["F","F1","20220105","20220108","IMP"],
            ["F","F2","20220105","20220108","IMP"],
            ["A","NOEND","20200104","","IMP"],
            ["A","OUTSIDE","20250101","20250103","IMP"],
        ],
        "patient": [
            ["A","1990","F","R1","E1"],
            ["B","2003","M","R2","E2"],
            ["C","1969","M","R3","E3"],
            ["E","1970","F","R4","E4"],
            ["F","1985","M","R5","E5"],
        ],
        "procedure": [
            ["A","AIP","20200105","CPT","70551"],
            ["A","AIP","20200106","CPT","70450"],
            ["A","AED","20200103","CPT","70498"],   # Not same IMP encounter
            ["A","AIP","20200201","CPT","70496"],   # Outside hospital stay
            ["A","AIP","20200105","SNOMED","70553"], # Different system
            ["C","CIP","20200110","CPT","70496"],
            ["E","EIP","20240301","CPT","70553"],
            ["F","F1","20220105","CPT","70551"],    # Tie patient excluded
        ],
    }
    headers = {stage: sorted(s.INPUT_COLUMNS[stage]) for stage in s.SOURCE}
    # Explicit source order; the code reads rows via CSV header names.
    order = {
        "diagnosis": ["patient_id","encounter_id","code_system","code","date","principal_diagnosis_indicator"],
        "encounter": ["patient_id","encounter_id","start_date","end_date","type"],
        "patient": ["patient_id","year_of_birth","sex","race","ethnicity"],
        "procedure": ["patient_id","encounter_id","date","code_system","code"],
    }
    details = {}
    manifest = {}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for stage, values in files.items():
            import io
            buf = io.StringIO(newline="")
            writer = csv.writer(buf)
            writer.writerow(order[stage])
            writer.writerows(values)
            payload = buf.getvalue().encode()
            z.writestr("synthetic/" + stage + ".csv", payload)
            details[stage+".csv"] = {"present": True, "headers": order[stage],
                                    "uncompressed_bytes": len(payload)}
            manifest[stage+".csv"] = {"row_count": len(values)}
    pre = tmp_path / "preflight.json"
    pre.write_text(json.dumps({
        "stage": "STEP36_RESEARCH_METADATA_PREFLIGHT",
        "clinical_rows_read": 0,
        "full_clinical_tables_scanned": False,
        "files": details, "relevant_manifest_counts": manifest,
    }))
    return archive, pre, folder


def test_date_and_stroke_candidates():
    assert s.parsedate("20240229") == "20240229"
    assert s.parsedate("2024-02-29") == "20240229"
    for bad in ("20230229", "20241301", "20200101x", "202001", "", None, "2020-02-30"):
        assert s.parsedate(bad) is None
    assert s.stroke_candidate("ICD-10-CM", "I63.9")
    assert s.stroke_candidate("ICD-10-CM", "I63")
    for system, code in (("ICD-9-CM", "I63.9"), ("ICD-10-CM", "I639"),
                         ("ICD-10-CM", "H34.1"), ("ICD-10-PCS", "I63.9")):
        assert not s.stroke_candidate(system, code)


@pytest.mark.parametrize("yob,sex,cohort,expected", [
    (1990,"F",s.COHORTS[0],"definite"),
    (2003,"M",s.COHORTS[0],"boundary_uncertain"),
    (1969,"M",s.COHORTS[0],"boundary_uncertain"),
    (1969,"M",s.COHORTS[1],"definite"),
    (1960,"F",s.COHORTS[1],"excluded"),
    (1960,"F",s.COHORTS[0],"excluded"),
    (None,"F",s.COHORTS[0],"unknown_yob"),
    (1990,"U",s.COHORTS[1],"unknown_sex"),
])
def test_age_interval(yob,sex,cohort,expected):
    assert s.age_class("20200105",yob,sex,cohort) == expected


def test_complete_synthetic_stages_and_primary_linkage(fake):
    z, pre, folder = fake
    for stage in s.STAGES:
        result = s.run(z, stage, preflight=pre, folder=folder, chunk=2)
        assert result["complete"]
    output = json.loads((folder/"aggregate_review_LOCAL_ONLY.json").read_text())
    assert output["imaging_completion_verified"] is False
    assert output["ED_date_only_sensitivity_included"] is False
    assert output["race_ethnicity_disparities_computed"] is False
    uniform = output["cohorts"][s.COHORTS[0]]
    historical = output["cohorts"][s.COHORTS[1]]
    assert uniform["indexed_patients_not_validated"] == 1
    assert historical["indexed_patients_not_validated"] == 3  # A, C and E (female E has age 53-54 in 2024)
    assert uniform["by_start_year"]["2020"]["with_P_label"] == 1
    assert uniform["primary_same_IMP_CPT14_code_capture_counts_NOT_performed_scans"] == {
        "CT_HEAD": 1, "MRI_BRAIN": 1}
    assert historical["primary_same_IMP_CPT14_code_capture_counts_NOT_performed_scans"] == {
        "CT_HEAD": 1, "CTA_HEAD": 1, "MRI_BRAIN": 2}
    serialized = json.dumps(output)
    for value in ("AIP","AED","SYNTH_STROKE_ONLY","patient_id","encounter_id"):
        assert value not in serialized
    assert stat.S_IMODE((folder / s.DB.name).stat().st_mode) == 0o600
    assert stat.S_IMODE((folder/"aggregate_review_LOCAL_ONLY.json").stat().st_mode) == 0o600
    with pytest.raises(ValueError, match="already completed"):
        s.run(z, "diagnosis", preflight=pre, folder=folder, chunk=2)


def test_resume_checkpoint_no_double_counts(fake):
    z, pre, folder = fake
    partial = s.run(z,"diagnosis",preflight=pre,folder=folder,chunk=2,stop_after=3)
    assert not partial["complete"]
    assert partial["processed_rows"] == 4
    continued = s.run(z,"diagnosis",preflight=pre,folder=folder,chunk=3)
    assert continued["complete"] and continued["processed_rows"] == 11
    with sqlite3.connect(str(folder/s.DB.name)) as db:
        assert db.execute("SELECT COUNT(*) FROM dx").fetchone()[0] == 7  # AIP,BIP,CIP,EIP,F1,F2,AED


def test_rejects_out_of_order_and_bad_ack(fake):
    z, pre, folder = fake
    with pytest.raises(ValueError, match="prior stage"):
        s.run(z, "procedure", preflight=pre, folder=folder)
    with pytest.raises(SystemExit):
        s.main(["--zip",str(z),"--stage","diagnosis","--acknowledge","WRONG"])


def test_fingerprint_rejects_changed_source_or_policy(fake):
    z, pre, folder = fake
    s.run(z,"diagnosis",preflight=pre,folder=folder,chunk=4,stop_after=4)
    obj = json.loads(pre.read_text())
    obj["unrelated_policy"] = "changed"
    pre.write_text(json.dumps(obj))
    with pytest.raises(ValueError, match="policy changed"):
        s.run(z,"diagnosis",preflight=pre,folder=folder)


def test_preflight_and_path_guards(fake, tmp_path):
    z, pre, folder = fake
    with pytest.raises(ValueError, match="gitignored private results"):
        s.run(z,"diagnosis",preflight=pre,folder=tmp_path/"OUT")
    bad = json.loads(pre.read_text())
    bad["files"]["encounter.csv"]["uncompressed_bytes"] += 1
    pre.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="signature mismatch"):
        s.run(z,"diagnosis",preflight=pre,folder=folder)


def test_no_unknown_cohort():
    with pytest.raises(ValueError, match="Unknown cohort"):
        s.age_class("20200101",1990,"F","not_a_cohort")
