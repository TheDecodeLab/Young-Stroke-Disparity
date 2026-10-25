"""Step83 disclosure-candidate tests use fabricated summary counts only."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/step83_disclosure_candidate.py"
SPEC = importlib.util.spec_from_file_location("step83_disclosure_candidate", SCRIPT)
s83 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s83)


def fixture_report():
    def rows(data):
        return [{"category": category,
                 "n_P0": p0, "n_P1": p1, "n_total": p0+p1,
                 "pct_P0": round(100*p0/100, 2),
                 "pct_P1": round(100*p1/50, 2),
                 "pct_total": round(100*(p0+p1)/150, 2)}
                for category, p0, p1 in data]
    tables = {
        "SEX": rows([("MALE", 50, 30), ("FEMALE", 35, 15), ("UNKNOWN_MISSING", 15, 5)]),
        "RACE": rows([("WHITE", 60, 25), ("BLACK_AFRICAN_AMERICAN", 40, 25)]),
        "ETHNICITY": rows([("HISPANIC_LATINO", 35, 20), ("NOT_HISPANIC_LATINO", 65, 30)]),
        "AGE_BAND": rows([("18-24", 30, 15), ("25-34", 70, 35)]),
        "INDEX_YEAR": rows([("2019", 45, 20), ("2020", 55, 30)]),
    }
    return {
        "policy": "STEP82_INTERNAL_ONLY_NOT_RELEASE_APPROVED",
        "baseline": {
            "n": 150, "P0": 100, "P1": 50,
            "category_tables": tables,
            "preliminary_small_cell_or_complement_flags": ["SEX:UNKNOWN_MISSING:P1"],
        },
        "patient_flow_not_full_export_flow": {
            "source_scope": "retained date-valid same-patient/encounter I63-coded IMP keys",
            "candidate_retained_imp_keys": 215,
            "candidate_unique_patients": 200,
            "patient_flow": {
                "included_indexed": 150,
                "held_competing_same_day_definite_index": 20,
                "no_definite_missing_birth_year": 30,
            },
            "patient_partition_reconciles": True,
            "indexed_patients_reconcile": 150,
        },
    }


def regenerated_flags(source):
    flags = []
    b = source["baseline"]
    for dim, rows in b["category_tables"].items():
        for r in rows:
            for k, den, label in (("n_total", b["n"], "total"),
                                  ("n_P0", b["P0"], "P0"),
                                  ("n_P1", b["P1"], "P1")):
                if s83.flagged(r[k], den):
                    flags.append(dim + ":" + r["category"] + ":" + label)
    b["preliminary_small_cell_or_complement_flags"] = flags


def test_one_sensitive_sex_cell_leads_to_entire_sex_p_suppression():
    result = s83.prepare(fixture_report())
    assert result["source_warning_count"] == 1
    assert result["dimension_policies"]["SEX"] == "overall_only"
    assert len(result["baseline"]["SEX"]) == 3
    assert all(set(r) == {"category", "total_n", "total_pct"}
               for r in result["baseline"]["SEX"])
    assert result["dimension_policies"]["RACE"] == "P_stratified"
    assert all("P0_n" in r and "P1_n" in r for r in result["baseline"]["RACE"])
    text = s83.as_markdown(result)
    assert "Not displayed" in text
    for line in text.splitlines():
        if line.startswith("| Source sex |"):
            assert line.count("Not displayed") == 2


def test_disclosure_flag_is_recomputed_and_source_tampering_fails():
    report = fixture_report()
    report["baseline"]["preliminary_small_cell_or_complement_flags"] = []
    with pytest.raises(AssertionError, match="disclosure flags"):
        s83.prepare(report)


def test_category_subtotals_and_percentages_fail_closed():
    report = fixture_report()
    report["baseline"]["category_tables"]["RACE"][0]["n_P1"] += 1
    with pytest.raises(AssertionError):
        s83.prepare(report)
    report = fixture_report()
    report["baseline"]["category_tables"]["SEX"][0]["pct_P1"] = 0.0
    with pytest.raises(AssertionError, match="percentage mismatch"):
        s83.prepare(report)


def test_other_dimension_p_flags_trigger_overall_only_not_partial_suppression():
    report = fixture_report()
    ethnicity = report["baseline"]["category_tables"]["ETHNICITY"]
    ethnicity[0].update(n_P0=100, n_P1=5, n_total=105, pct_P0=100.0,
                        pct_P1=10.0, pct_total=70.0)
    ethnicity[1].update(n_P0=0, n_P1=45, n_total=45, pct_P0=0.0,
                        pct_P1=90.0, pct_total=30.0)
    regenerated_flags(report)
    candidate = s83.prepare(report)
    assert candidate["dimension_policies"]["ETHNICITY"] == "overall_only"
    assert all("P1_n" not in r for r in candidate["baseline"]["ETHNICITY"])


def test_small_total_flag_withholds_whole_dimension():
    report = fixture_report()
    race = report["baseline"]["category_tables"]["RACE"]
    race[0].update(n_P0=2, n_P1=3, n_total=5, pct_P0=2.0,
                   pct_P1=6.0, pct_total=round(100*5/150, 2))
    race[1].update(n_P0=98, n_P1=47, n_total=145, pct_P0=98.0,
                   pct_P1=94.0, pct_total=round(100*145/150, 2))
    regenerated_flags(report)
    candidate = s83.prepare(report)
    assert candidate["dimension_policies"]["RACE"] == "withheld_entire_dimension"
    assert "RACE" not in candidate["baseline"]


def test_flow_rare_reason_collapses_all_other_exclusions():
    report = fixture_report()
    part = report["patient_flow_not_full_export_flow"]["patient_flow"]
    part["held_competing_same_day_definite_index"] = 5
    part["no_definite_missing_birth_year"] = 45
    candidate = s83.prepare(report)
    assert candidate["selection"]["grouping_policy"] == "collapsed_exclusions"
    assert candidate["selection"]["mutually_exclusive_patient_groups"] == [
        {"reason": "Included indexed patients", "n": 150},
        {"reason": "Not indexed for eligibility or tie reasons", "n": 50},
    ]


def test_flow_with_small_nonindexed_complement_is_withheld():
    report = fixture_report()
    report["patient_flow_not_full_export_flow"].update(candidate_unique_patients=155)
    part = report["patient_flow_not_full_export_flow"]["patient_flow"]
    part["held_competing_same_day_definite_index"] = 0
    part["no_definite_missing_birth_year"] = 5
    with pytest.raises(ValueError, match="small retained/excluded group"):
        s83.prepare(report)


def test_private_writer_owner_only_and_no_overwrite(monkeypatch, tmp_path):
    root = tmp_path / "results/phase1/full_reconstruction_private"
    root.mkdir(parents=True)
    monkeypatch.setattr(s83, "PRIVATE_ROOT", root)
    output = s83._write_private(root / "step83", {"candidate.md": "synthetic"})
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE((output / "candidate.md").stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        s83._write_private(output, {"candidate.md": "overwriting"})
    with pytest.raises(ValueError):
        s83._write_private(tmp_path / "unsafe", {"file": "x"})


def test_cli_direct_execution_with_fabricated_step82_json(tmp_path):
    import shutil
    import subprocess
    import sys
    root = tmp_path / "fake-repo"
    sdir = root / "scripts"
    sdir.mkdir(parents=True)
    shutil.copy2(SCRIPT, sdir / SCRIPT.name)
    private = root / "results/phase1/full_reconstruction_private"
    step82 = private / "step82_submission_reporting_private"
    step82.mkdir(parents=True)
    (step82 / "cohort_flow_baseline_INTERNAL_ONLY.json").write_text(
        json.dumps(fixture_report()), encoding="utf-8")
    p = subprocess.run([sys.executable, str(sdir / SCRIPT.name),
                        "--acknowledge", s83.ACK], cwd=root,
                       capture_output=True, text=True, timeout=20)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "SEX publication candidate policy: overall_only" in p.stdout
    output = private / "step83_reporting_candidate_private"
    candidate = json.loads((output / "reporting_candidate_LOCAL_ONLY.json").read_text())
    assert candidate["dimension_policies"]["SEX"] == "overall_only"
    assert (output / "reporting_candidate_LOCAL_ONLY.md").exists()