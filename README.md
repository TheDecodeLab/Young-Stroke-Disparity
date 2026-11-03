# Young Stroke Neuroimaging: Encounter Attribution and Recorded Procedure Codes

**Research code repository. Publication release is currently blocked pending the [release audit](docs/PUBLICATION_RELEASE_AUDIT_2026-11-02.md).**

This project examines how attributing recorded neuroimaging procedure codes to different encounters changes reported code capture among young adults with ischemic-stroke diagnosis codes. It studies the measurement properties of administrative data. Recorded procedure codes do not establish completed imaging, episode membership, or clinical care quality.

## CURRENT PLAN OF RECORD

The active development branch is `analysis-rebuild-phase1-audit`. The original `master` branch retains the older Diamond/NIS research history. Pull request [#1](https://github.com/TheDecodeLab/Young-Stroke-Disparity/pull/1) remains **draft and unmerged** while publication and historical data-governance checks are pending.

The primary study uses a locally held TriNetX Research Network export. The analysis defines an index inpatient I63-coded encounter and measures neuroimaging code presence under alternative encounter attribution rules. Exploratory comparisons include demographic coding and encounter-key ambiguity. A separate historical TriNetX Diamond measurement analysis is descriptive context, not external validation. Historical NIS work is not part of the current inferential study.

## Reproducibility

- Pipeline and staged consistency tests: [`scripts/`](scripts/) and [`tests/`](tests/)
- Step 88, paired demographic contrasts and patient-equivalent bootstrap: [`scripts/step88_paired_demographic_rule_contrasts.py`](scripts/step88_paired_demographic_rule_contrasts.py)
- Step 89, source-header and medication/procedure feasibility: [`scripts/step89_treatment_source_feasibility.py`](scripts/step89_treatment_source_feasibility.py)
- Historical measurement-window sensitivity: [`docs/STEP87_S3_AGGREGATE_VALIDATION.md`](docs/STEP87_S3_AGGREGATE_VALIDATION.md)
- Public file safety gate: [`scripts/check_public_release_tree.py`](scripts/check_public_release_tree.py)

Synthetic tests can run without source clinical datasets. Primary empirical analyses require access to the approved local research datasets and private checkpoints. The source ZIP, patient-level intermediate tables, and manuscript-specific protected aggregates are **not intended for redistribution** in this code repository. See the source-specific approved access conditions for any release authorization.

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/check_public_release_tree.py
```

The last command intentionally fails until historical tracked data and notebooks are reviewed or removed from the releasable tree. **A passing unit-test suite does not authorize publication of the repository or its data.**

## Historical development and release status

Earlier staged Methods and data-quality decision records remain in [`docs/`](docs/) and Git history as historical implementation records. The research was conducted under an approved Penn State research protocol. The earlier [Research Network pre-reconstruction gate](docs/RESEARCH_NETWORK_PRE_RECONSTRUCTION_GATE.md), [data steward request](docs/RESEARCH_NETWORK_DATA_STEWARD_REQUEST.md), and Step58 local bounded technical pilot document planning stages that preceded the completed Research Network reconstruction. The [imaging code citation register](docs/IMAGING_CODE_CITATION_REGISTER.md) also records historical codebook work. Some reflect hypotheses or implementation states later superseded by the Research Network reconstruction. Do not use them as current manuscript results without verifying the corresponding version.

The public repository presently contains a legacy derived patient-level Parquet dataset and a notebook with saved outputs. A previous manuscript draft also exists in older commit history. Publication requires an approved disposition for those files and a history-remediation plan. Simply deleting a file at the current commit or merging the active branch does not remove it from Git history.

For the exact release blockers, branch cleanup sequence, and checks, see [Publication release audit](docs/PUBLICATION_RELEASE_AUDIT_2026-11-02.md).

## License

See [`LICENSE`](LICENSE) for code licensing. That code license does **not** grant rights to redistribute clinical research datasets or third-party codebooks and source materials.
