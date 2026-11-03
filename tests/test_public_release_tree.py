"""Synthetic-only checks for publication tree safety."""
import json
from scripts.check_public_release_tree import inspect_paths


def test_rejects_binary_patient_dataset(tmp_path):
    path = tmp_path / "dataset"
    path.mkdir()
    (path / "demo.parquet").write_bytes(b"SYNTHETIC")
    issues = inspect_paths(tmp_path, ["dataset/demo.parquet"])
    assert issues == [("dataset/demo.parquet", "binary or archived data file")]


def test_output_bearing_notebook_is_rejected(tmp_path):
    notebook = {"cells": [{"cell_type": "code", "execution_count": 1,
                           "source": ["print(1)"],
                           "outputs": [{"output_type": "stream", "text": ["1"]}]}]}
    (tmp_path / "old.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
    assert "notebook contains" in inspect_paths(tmp_path, ["old.ipynb"])[0][1]


def test_clean_notebook_passes(tmp_path):
    notebook = {"cells": [{"cell_type": "code", "execution_count": None,
                           "source": ["print(1)"], "outputs": []}]}
    (tmp_path / "clean.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
    assert inspect_paths(tmp_path, ["clean.ipynb"]) == []


def test_historical_study_aggregate_is_flagged(tmp_path):
    issues = inspect_paths(tmp_path, ["dataset/MRI_CT_Summary_with_pvalues.csv"])
    assert "historical study aggregate" in issues[0][1]


def test_public_codebooks_allowed(tmp_path):
    assert inspect_paths(tmp_path, ["dataset/imaging_codebook_candidate_v1.csv",
                                    "docs/references/imaging_references.ris"]) == []


def test_private_names_rejected(tmp_path):
    cases = ["results/analysis.json", "deep/results/cohort.json",
             "output_LOCAL_ONLY.json", "data/credentials.pem"]
    assert len(inspect_paths(tmp_path, cases)) == len(cases)


def test_invalid_notebook_fails_without_printing_content(tmp_path):
    (tmp_path / "bad.ipynb").write_text("{bad", encoding="utf-8")
    assert inspect_paths(tmp_path, ["bad.ipynb"]) == [
        ("bad.ipynb", "notebook cannot be safely parsed")
    ]
