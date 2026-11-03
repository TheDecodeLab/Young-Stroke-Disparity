"""Step 34: build internal, aggregate-only manuscript exhibits.

Inputs are approved-for-internal-analysis Steps 25/31/33 JSON files.
Creates local CSV tables and PNG/SVG figures under results/ only.
Does not read source ZIP, private SQLite, or person-level records.
NOT for public disclosure until institutional cross-table review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW_KEYS = ('0', '1', '3', '7')

WINDOWS = ("0", "1", "3", "7")
GROUPS = ("age_band", "recorded_sex", "index_year")
LABELS = {"0": "Same day", "1": "+/-1 day",
          "3": "+/-3 days", "7": "+/-7 days"}


def require(test: bool, message: str) -> None:
    if not test:
        raise ValueError("Step 34 input reconciliation failed: " + message)


def pct(count: int, denominator: int) -> float:
    return round(100.0 * count / denominator, 2)


def build_data(step25: dict, step31: dict, step33: dict) -> dict:
    require(step25.get("all_prior_aggregate_counts_reconciled") is True
            and step25.get("ready_for_manuscript_inference") is False,
            "Step25 provenance/inference status")
    require(step31.get("stage") ==
            "STEP31_EXPANDED_IMAGING_AGGREGATE_RECONCILIATION"
            and step31.get("all_aggregate_checks_passed") is True
            and step31.get("cross_report_disclosure_review_required") is True,
            "Step31 source gate")
    require(step33.get("stage") ==
            "STEP33_AGGREGATE_RECORDING_PATTERN_DESCRIPTIVES"
            and step33.get("all_three_dimensions_reconciled") is True
            and step33.get("cross_table_disclosure_review_required") is True
            and step33.get("clinical_inference_allowed") is False
            and step33.get("demographic_disparity_inference_allowed") is False,
            "Step33 source/clinical gate")
    n = step25["approximate_age_19_50_eligible_patients"]
    require(n == step31["study_cohort_n"] == step33["denominator"]
            and n > 0, "denominator disagreement")
    require(step25["principal_I63_index_patients"] >= n,
            "diagnosis cohort inconsistent")
    windows = []
    for w in WINDOWS:
        a = step31["per_window"][w]
        require(a["denominator"] == n and not a["small_delta_suppressed"],
                "window withheld or denominator changed: " + w)
        historical = a["legacy_with_any_included_code_n"]
        head = a["head_only_with_any_included_code_n"]
        expanded = a["expanded_with_any_included_code_n"]
        require(0 <= historical <= head <= expanded <= n,
                "non-nested procedure code sets: " + w)
        # Cross-table arithmetic can expose an apparently suppressed small
        # increment even if every published marginal itself exceeds 11.
        for value in (historical, head, expanded, n - expanded,
                      head-historical, expanded-head):
            require(value == 0 or value >= 11,
                    "potentially disclosive window count: " + w)
        require(pct(head, n) ==
                step33["window_head_only_any_code_percent"][w],
                "head-only rounded percentage mismatch: " + w)
        require(pct(expanded, n) ==
                step33["window_expanded_any_code_percent"][w],
                "head+neck rounded percentage mismatch: " + w)
        windows.append({
            "window": LABELS[w], "window_days_each_side": int(w),
            "denominator": n,
            "historical_9_code_any_n": historical,
            "historical_9_code_any_percent": pct(historical, n),
            "head_only_14_code_any_n": head,
            "head_only_14_code_any_percent": pct(head, n),
            "head_neck_14_code_any_n": expanded,
            "head_neck_14_code_any_percent": pct(expanded, n),
            "head_neck_no_matched_code_n": n - expanded,
            "head_neck_no_matched_code_percent": pct(n - expanded, n),
        })
    # Check all margin descriptions against the same fixed denominator.
    demographics = []
    source = step33["code_match_rates_by_group_head_only_and_expanded"]
    require(set(source) == set(GROUPS), "missing or extra study strata")
    for group in GROUPS:
        members = source[group]
        require(sum(x["denominator"] for x in members) == n,
                "dimension denominator sum: " + group)
        require(sum(x["head_only_any_code_n"] for x in members)
                == windows[1]["head_only_14_code_any_n"], 
                "head-only count margin: " + group)
        require(sum(x["expanded_head_plus_neck_any_code_n"]
                    for x in members) ==
                windows[1]["head_neck_14_code_any_n"],
                "head+neck count margin: " + group)
        for person_group in members:
            denominator = person_group["denominator"]
            head = person_group["head_only_any_code_n"]
            wide = person_group["expanded_head_plus_neck_any_code_n"]
            require(0 <= head <= wide <= denominator,
                    "non-nested group count: " + group)
            for value in (denominator, head, wide, denominator-wide,
                          wide-head):
                require(value == 0 or value >= 11,
                        "potentially disclosive subgroup count: " + group)
            require(pct(head, denominator) ==
                    person_group["head_only_any_code_percent"],
                    "head-only group percentage: " + group)
            require(pct(wide, denominator) ==
                    person_group["expanded_head_plus_neck_any_code_percent"],
                    "expanded group percentage: " + group)
            demographics.append({
                "dimension": group,
                "stratum": person_group["stratum"],
                "denominator": denominator,
                "head_only_any_n": head,
                "head_only_any_percent": pct(head, denominator),
                "head_neck_any_n": wide,
                "head_neck_any_percent": pct(wide, denominator),
            })
    return {"cohort_n": n, "diagnosis_index_n":
            step25["principal_I63_index_patients"],
            "windows": windows, "strata": demographics,
            "missingness_percent": step25["descriptive_missingness_percent"],
            "clinical_inference_allowed": False,
            "requires_disclosure_review": True}


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_figures(data: dict, out: Path) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "Step34 requires matplotlib; install it in the study virtualenv"
        ) from exc

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 14,
        "axes.labelsize": 16,
        "axes.titlesize": 17,
        "legend.fontsize": 12,
        "xtick.labelsize": 13,
        "ytick.labelsize": 13,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })
    files = []
    win = data["windows"]
    x = list(range(4))
    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    for key, label, marker, line in (
        ("historical_9_code_any_percent", "Historical 9 codes", "o", "--"),
        ("head_only_14_code_any_percent", "Head-only 14-code catalog", "s", "-"),
        ("head_neck_14_code_any_percent", "Head + neck 14-code catalog", "^", "-."),
    ):
        ax.plot(x, [r[key] for r in win], marker=marker, markersize=9,
                linewidth=2.5, linestyle=line, label=label)
    ax.set_xticks(x, [r["window"] for r in win])
    ax.set_ylim(0, 60)
    ax.set_ylabel("Patients with a matching listed CPT code (%)")
    ax.set_xlabel("Calendar-day window around first observed I63 diagnosis")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        name = "figure2_code_match_by_window." + ext
        fig.savefig(out / name, dpi=250)
        files.append(name)
    plt.close(fig)

    for dim, label in (
        ("age_band", "Approximate age at diagnosis (years)"),
        ("recorded_sex", "Recorded sex"),
        ("index_year", "Index diagnosis year"),
    ):
        rows = [r for r in data["strata"] if r["dimension"] == dim]
        y = list(range(len(rows)))
        fig, ax = plt.subplots(figsize=(10.5, max(4.4, len(rows) * 1.35 + 2.2)))
        ax.scatter([r["head_only_any_percent"] for r in rows], y,
                   s=135, marker="o", label="Head only", zorder=3)
        ax.scatter([r["head_neck_any_percent"] for r in rows], y,
                   s=100, marker="D", label="Head + neck", zorder=4)
        for idx, row in enumerate(rows):
            ax.plot([row["head_only_any_percent"], row["head_neck_any_percent"]],
                    [idx, idx], linewidth=2, alpha=0.45)
            ax.annotate(f'{row["head_only_any_percent"]:.2f}%',
                        (row["head_only_any_percent"], idx),
                        textcoords="offset points", xytext=(-6, 12),
                        ha="right", fontsize=11)
        ax.set_yticks(y, [r["stratum"] for r in rows])
        ax.invert_yaxis()
        ax.set_xlim(0, 65)
        ax.set_xlabel("Patients with a matching listed CPT code (%)")
        ax.set_ylabel(label)
        ax.grid(axis="x", alpha=0.2)
        ax.legend(frameon=False, loc="lower right")
        fig.tight_layout()
        for ext in ("png", "svg"):
            name = "figure3_" + dim + "_code_recording." + ext
            fig.savefig(out / name, dpi=250)
            files.append(name)
        plt.close(fig)
    return files


def run(step25_path: Path, step31_path: Path, step33_path: Path,
        out_dir: Path) -> dict:
    paths = (step25_path, step31_path, step33_path)
    data = build_data(*(json.loads(p.read_text(encoding="utf-8"))
                        for p in paths))
    resolved = out_dir.expanduser().resolve()
    results_dir = (ROOT / "results").resolve()
    require(results_dir == resolved or results_dir in resolved.parents,
            "exhibits must stay under gitignored results/ directory")
    out_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(out_dir, 0o700)
    win_path = out_dir / "table2_temporal_code_definitions.csv"
    strata_path = out_dir / "table3_unadjusted_code_frequency.csv"
    write_csv(win_path, data["windows"])
    write_csv(strata_path, data["strata"])
    images = make_figures(data, out_dir)
    artifacts = [win_path.name, strata_path.name, *images]
    manifest = {
        "stage": "STEP34_INTERNAL_AGGREGATE_MANUSCRIPT_EXHIBITS",
        "denominator": data["cohort_n"],
        "only_aggregate_json_inputs": True,
        "source_zip_rows_scanned": 0,
        "private_sqlite_rows_read": 0,
        "clinical_inference_allowed": False,
        "public_release_approved": False,
        "cross_table_disclosure_review_required": True,
        "input_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths
        },
        "artifacts": {
            name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
            for name in artifacts
        },
        "warning": (
            "Figures describe matching procedure CODE records, not "
            "performed clinical imaging, hospitalization, care quality, "
            "or demographic access disparities."
        )
    }
    manifest_path = out_dir / "step34_internal_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True)
                             + "\n", encoding="utf-8")
    for name in (*artifacts, manifest_path.name):
        os.chmod(out_dir / name, 0o600)
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--step25", type=Path, required=True)
    p.add_argument("--step31", type=Path, required=True)
    p.add_argument("--step33", type=Path, required=True)
    p.add_argument("--out-dir", type=Path,
                   default=Path("results/phase1/step34_internal_exhibits"))
    args = p.parse_args()
    result = run(args.step25, args.step31, args.step33, args.out_dir)
    print("Internal only. Aggregate manuscript exhibits:", args.out_dir)
    print("Figures/tables:", len(result["artifacts"]))
    print("No clinical source records read. Disclosure review remains REQUIRED.")


if __name__ == "__main__":
    main()
