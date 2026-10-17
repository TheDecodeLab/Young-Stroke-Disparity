"""Synthetic-only Step36 tests: no private data access."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from scripts.step36_research_zip_preflight import positive_int, find_csv_files

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "step36_research_zip_preflight.py"
HEADERS = {
    "patient.csv": "patient_id,sex,race,ethnicity,year_of_birth\n",
    "patient_cohort.csv": "patient_id,cohort_name,cohort_number\n",
    "encounter.csv": "encounter_id,patient_id,start_date,end_date,type\n",
    "diagnosis.csv": "patient_id,encounter_id,code_system,code,date,principal_diagnosis_indicator\n",
    "procedure.csv": "patient_id,encounter_id,code_system,code,date\n",
}


def make_zip(path, *, encounter=True, duplicate=False):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, header in HEADERS.items():
            if not encounter and name == "encounter.csv":
                continue
            z.writestr("export/" + name, header + "PRIVATE_TEST_PATIENT,100,200\n")
        if duplicate:
            z.writestr("second/diagnosis.csv", HEADERS["diagnosis.csv"])
        z.writestr("export/manifest.csv", "file,column_count,row_count,unique_patient_count\n"
                   "patient.csv,5,300,300\nencounter.csv,5,900,300\n"
                   "diagnosis.csv,6,1200,300\nprocedure.csv,5,1900,300\n")
        z.writestr("export/dataset_details.csv",
                   "total_number_unique_patients,total_number_HCOs,date_created,network_name\n"
                   "300,2,20250829,Research\n")
        z.writestr("export/cohort_details.csv",
                   "cohort_name,cohort_number,total_patient_records\nResearch-Stroke-ICDs,1,300\n")


def run_cli(source, output, bundle=None):
    cmd = [sys.executable, str(SCRIPT), "--zip", str(source), "--output", str(output)]
    if bundle is not None:
        cmd += ["--output-zip", str(bundle)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_metadata_only_and_bundle(tmp_path):
    source, output, bundle = (tmp_path / s for s in ("source.zip", "report.json", "review.zip"))
    make_zip(source)
    run = run_cli(source, output, bundle)
    assert run.returncode == 0, run.stderr
    obj = json.loads(output.read_text())
    assert obj["schema_supports_attempted_encounter_linkage"] is True
    assert obj["clinical_rows_read"] == 0
    assert obj["encounter_linkage_verified"] is False
    assert obj["inpatient_classification_verified"] is False
    assert obj["relevant_manifest_counts"]["diagnosis.csv"]["row_count"] == 1200
    assert "PRIVATE_TEST_PATIENT" not in output.read_text()
    assert output.stat().st_mode & 0o077 == 0
    assert bundle.stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(bundle) as z:
        assert z.namelist() == ["step36_research_metadata_preflight.json"]
        assert json.loads(z.read(z.namelist()[0])) == obj


def test_missing_encounter_blocks_readiness(tmp_path):
    source, output = tmp_path / "source.zip", tmp_path / "report.json"
    make_zip(source, encounter=False)
    run = run_cli(source, output)
    assert run.returncode == 0, run.stderr
    obj = json.loads(output.read_text())
    assert obj["schema_supports_attempted_encounter_linkage"] is False
    assert "missing required table: encounter.csv" in obj["warnings"]


def test_duplicate_basename_blocks_readiness(tmp_path):
    source, output = tmp_path / "source.zip", tmp_path / "report.json"
    make_zip(source, duplicate=True)
    run = run_cli(source, output)
    assert run.returncode == 0, run.stderr
    assert json.loads(output.read_text())["schema_supports_attempted_encounter_linkage"] is False


def test_numeric_parser():
    assert positive_int("12") == 12
    assert positive_int("0") == 0
    assert positive_int("-1") is None
    assert positive_int("2.4") is None


def test_output_collision_is_rejected(tmp_path):
    source, output = tmp_path / "source.zip", tmp_path / "same"
    make_zip(source)
    result = run_cli(source, output, output)
    assert result.returncode != 0
    assert "must differ" in result.stderr
    assert not output.exists()


def test_member_lookup(tmp_path):
    source = tmp_path / "source.zip"
    make_zip(source)
    with zipfile.ZipFile(source) as z:
        mapping, warnings = find_csv_files(z)
    assert not warnings
    assert mapping["procedure.csv"] == "export/procedure.csv"
