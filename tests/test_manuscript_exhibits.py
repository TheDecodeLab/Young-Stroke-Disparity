"""Synthetic source-only Step34 tests: never read private or source records."""
from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.step34_manuscript_exhibits import build_data, pct, run


def fixture():
    n = 600
    windows = {}
    numbers = {
        "0": (180, 200, 240),
        "1": (230, 260, 300),
        "3": (270, 300, 340),
        "7": (300, 330, 370),
    }
    for window, (old, head, wide) in numbers.items():
        windows[window] = {
            "denominator": n, "small_delta_suppressed": False,
            "legacy_with_any_included_code_n": old,
            "head_only_with_any_included_code_n": head,
            "expanded_with_any_included_code_n": wide,
        }
    strata_values = {
        "age_band": [
            ("19-29", 100, 60, 70),
            ("30-39", 200, 90, 100),
            ("40-50", 300, 110, 130),
        ],
        "recorded_sex": [
            ("Female", 250, 120, 135),
            ("Male", 350, 140, 165),
        ],
        "index_year": [
            ("2018", 300, 120, 140),
            ("2019", 300, 140, 160),
        ],
    }
    groups = {}
    for key, rows in strata_values.items():
        groups[key] = [{
            "stratum": name, "denominator": denominator,
            "head_only_any_code_n": head,
            "head_only_any_code_percent": pct(head, denominator),
            "expanded_head_plus_neck_any_code_n": wide,
            "expanded_head_plus_neck_any_code_percent": pct(wide, denominator),
        } for name, denominator, head, wide in rows]
    step25 = {
        "all_prior_aggregate_counts_reconciled": True,
        "ready_for_manuscript_inference": False,
        "approximate_age_19_50_eligible_patients": n,
        "principal_I63_index_patients": 800,
        "descriptive_missingness_percent": {"race_unknown": 75.0},
    }
    step31 = {
        "stage": "STEP31_EXPANDED_IMAGING_AGGREGATE_RECONCILIATION",
        "all_aggregate_checks_passed": True,
        "cross_report_disclosure_review_required": True,
        "study_cohort_n": n,
        "per_window": windows,
    }
    step33 = {
        "stage": "STEP33_AGGREGATE_RECORDING_PATTERN_DESCRIPTIVES",
        "all_three_dimensions_reconciled": True,
        "cross_table_disclosure_review_required": True,
        "clinical_inference_allowed": False,
        "demographic_disparity_inference_allowed": False,
        "denominator": n,
        "window_head_only_any_code_percent": {
            w: pct(x[1], n) for w, x in numbers.items()},
        "window_expanded_any_code_percent": {
            w: pct(x[2], n) for w, x in numbers.items()},
        "code_match_rates_by_group_head_only_and_expanded": groups,
    }
    return step25, step31, step33


def test_internal_aggregate_manuscript_data_validates():
    result = build_data(*fixture())
    assert result["cohort_n"] == 600
    assert len(result["windows"]) == 4
    assert len(result["strata"]) == 7
    assert result["windows"][1]["head_only_14_code_any_n"] == 260
    assert result["windows"][1]["head_neck_14_code_any_n"] == 300
    assert result["clinical_inference_allowed"] is False
    assert result["requires_disclosure_review"] is True


def test_denominator_drift_rejected():
    x = deepcopy(fixture())
    x[2]["denominator"] += 1
    with pytest.raises(ValueError, match="denominator"):
        build_data(*x)


def test_unsupported_inference_flag_rejected():
    x = deepcopy(fixture())
    x[2]["clinical_inference_allowed"] = True
    with pytest.raises(ValueError, match="Step33"):
        build_data(*x)


def test_nested_source_count_failure_rejected():
    x = deepcopy(fixture())
    x[1]["per_window"]["1"]["expanded_with_any_included_code_n"] = 250
    with pytest.raises(ValueError, match="non-nested"):
        build_data(*x)


def test_group_marginal_difference_rejected():
    x = deepcopy(fixture())
    x[2]["code_match_rates_by_group_head_only_and_expanded"][
        "recorded_sex"][0]["head_only_any_code_n"] -= 1
    with pytest.raises(ValueError, match="head-only count margin"):
        build_data(*x)


def test_small_nested_increment_rejected():
    x = deepcopy(fixture())
    a = x[1]["per_window"]["1"]
    a["expanded_with_any_included_code_n"] = (
        a["head_only_with_any_included_code_n"] + 5)
    with pytest.raises(ValueError, match="potentially disclosive"):
        build_data(*x)


def test_output_path_must_be_ignored_results_directory(tmp_path):
    import json
    a, b, c = fixture()
    paths = []
    for i, doc in enumerate((a, b, c)):
        p = tmp_path / f"{i}.json"
        p.write_text(json.dumps(doc))
        paths.append(p)
    with pytest.raises(ValueError, match="gitignored results"):
        run(*paths, tmp_path / "in_repository")


def test_real_figures_written_only_inside_results(tmp_path):
    pytest.importorskip("matplotlib")
    import json
    from scripts.step34_manuscript_exhibits import ROOT
    a, b, c = fixture()
    paths = []
    for i, doc in enumerate((a, b, c)):
        p = tmp_path / f"{i}.json"
        p.write_text(json.dumps(doc))
        paths.append(p)
    # Use dedicated synthetic directory within ignored results.
    output = ROOT / "results" / "test_step34_internal"
    try:
        manifest = run(*paths, output)
        assert manifest["public_release_approved"] is False
        assert manifest["cross_table_disclosure_review_required"] is True
        assert len(manifest["artifacts"]) == 10
        assert (output / "figure2_code_match_by_window.svg").exists()
        assert (output / "table3_unadjusted_code_frequency.csv").exists()
    finally:
        import shutil
        shutil.rmtree(output, ignore_errors=True)
