"""Step 22: check complete private SQLite reconstruction WITHOUT rereading ZIP.

This audit is exploratory, NOT encounter-validated utilization, admission
rates, clinical disparities, or a substitute for an approved codebook.
Source patient IDs and dates are read into local memory for aggregation
but NEVER exported; results JSON contains aggregate counts only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import stat

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COHORT_NAME = 'demographics/step19_age_cohort.sqlite'
IMAGING_NAME = 'imaging/step20_imaging_events.sqlite'
DX_NAME = 'diagnosis/step18_diagnosis_index.sqlite'
CLASSES = ('CT only', 'CT + additional', 'Additional without CT', 'None of four')
MODALITIES = ('CT', 'MRI', 'CTA', 'MRA')
SUMMARY_KEYS = {
    'age_eligible_first_diagnosis_n': 'total',
    'ct_n': 'CT', 'mri_n': 'MRI', 'cta_n': 'CTA', 'mra_n': 'MRA',
    'ct_only_n': 'CT only', 'ct_and_additional_n': 'CT + additional',
    'advanced_no_ct_n': 'Additional without CT',
    'none_of_four_imaging_n': 'None of four',
}


def read_complete_db(path: Path, table: str, cols: str) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f'Expected completed private database: {path.name}')
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        state = db.execute("SELECT value FROM scan_state WHERE key='scan_complete'").fetchone()
        if state is None or state[0] != '1':
            raise ValueError(f'Database not marked complete: {path.name}')
        return pd.read_sql_query(f'SELECT {cols} FROM {table}', db)


def classify(cohort: pd.DataFrame, events: pd.DataFrame, days: int) -> pd.DataFrame:
    if days < 0 or days > 7:
        raise ValueError('Only 0-7 day temporal windows are supported')
    included = events.loc[events['offset_days'].abs().le(days)]
    out = cohort[['patient_id', 'index_date', 'sex', 'age', 'race', 'ethnicity']].copy()
    for mod in MODALITIES:
        ids = set(included.loc[included['modality'].eq(mod), 'patient_id'])
        out[mod] = out['patient_id'].isin(ids)
    additional = out[['MRI', 'CTA', 'MRA']].any(axis=1)
    out['imaging_class'] = np.select(
        [out['CT'] & ~additional, out['CT'] & additional,
         ~out['CT'] & additional], CLASSES[:3], default=CLASSES[3])
    return out


def counts(frame: pd.DataFrame) -> dict:
    result = {'total': int(len(frame))}
    result.update({m: int(frame[m].sum()) for m in MODALITIES})
    result.update({key: int(frame['imaging_class'].eq(key).sum()) for key in CLASSES})
    if result['total'] != sum(result[k] for k in CLASSES):
        raise ValueError('Imaging classes fail to partition denominator')
    if result['CT'] != result['CT only'] + result['CT + additional']:
        raise ValueError('CT flag and CT strata disagree')
    return result


def is_unknown(value: pd.Series) -> pd.Series:
    text = value.astype('string').str.strip().str.lower()
    return (text.isna() | text.isin(['', 'unknown', 'nan', 'null', 'xxx',
                                    'not recorded', 'not reported']))


def group_summary(frame: pd.DataFrame, group_fields: list[str], threshold: int = 11) -> list[dict]:
    """Omit entire small strata rather than disclosing complementary cells."""
    if threshold < 11:
        raise ValueError('Disclosure threshold must be at least 11')
    output = []
    for grouping, part in frame.groupby(group_fields, dropna=False, sort=True, observed=True):
        if not isinstance(grouping, tuple):
            grouping = (grouping,)
        values = counts(part)
        # Suppress entire stratum if any strictly positive count is too small.
        if any(0 < val < threshold for val in values.values()):
            output.append({'stratum': dict(zip(group_fields, map(str, grouping))),
                           'suppressed': True})
        else:
            output.append({'stratum': dict(zip(group_fields, map(str, grouping))),
                           'suppressed': False, 'counts': values})
    return output


def verify_index(cohort: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    required_cohort = {'patient_id', 'index_date', 'sex', 'age', 'race', 'ethnicity'}
    required_events = {'patient_id', 'procedure_date', 'modality'}
    if missing := required_cohort - set(cohort):
        raise ValueError(f'Missing cohort fields: {sorted(missing)}')
    if missing := required_events - set(events):
        raise ValueError(f'Missing imaging fields: {sorted(missing)}')
    if cohort['patient_id'].isna().any() or cohort['patient_id'].duplicated().any():
        raise ValueError('Missing or duplicated patient keys in eligible table')
    if events['patient_id'].isna().any() or not events['modality'].isin(MODALITIES).all():
        raise ValueError('Invalid patient or modality in imaging table')
    dates = pd.to_datetime(cohort['index_date'], format='%Y%m%d', errors='coerce')
    if dates.isna().any() or not dates.dt.year.isin([2018, 2019]).all():
        raise ValueError('Invalid index date or year')
    if not cohort['age'].between(19, 50).all():
        raise ValueError('Saved cohort contains age outside 19-50')
    if not cohort['sex'].isin(['Male', 'Female']).all():
        raise ValueError('Unsupported sex label')
    if events.duplicated(['patient_id', 'modality', 'procedure_date']).any():
        raise ValueError('Duplicated modality-day receipt')
    joined = events.merge(cohort[['patient_id', 'index_date']], on='patient_id',
                          how='left', validate='many_to_one', indicator=True)
    if not joined['_merge'].eq('both').all():
        raise ValueError('Imaging record refers to noneligible patient')
    event_dates = pd.to_datetime(joined['procedure_date'], format='%Y%m%d', errors='coerce')
    index_dates = pd.to_datetime(joined['index_date'], format='%Y%m%d', errors='coerce')
    if event_dates.isna().any():
        raise ValueError('Invalid procedure date in imaging table')
    joined['offset_days'] = (event_dates - index_dates).dt.days
    if not joined['offset_days'].between(-7, 7).all():
        raise ValueError('Saved event is outside historical +/-7 window')
    return joined[['patient_id', 'modality', 'offset_days']]


def evaluate(cohort: pd.DataFrame, events: pd.DataFrame,
             prior: dict | None = None) -> dict:
    joined = verify_index(cohort, events)
    window_reports = {}
    widest = None
    for days in (0, 1, 3, 7):
        flags = classify(cohort, joined, days)
        window_reports[str(days)] = counts(flags)
        if days == 7:
            widest = flags
    if widest is None:
        raise AssertionError('Seven-day window missing')
    diffs = {}
    if prior is not None:
        original = prior['stages'][-1]['aggregate_cohort_integrity']
        for old_key, our_key in SUMMARY_KEYS.items():
            got = window_reports['7'][our_key]
            expected = int(original[old_key])
            if expected != got:
                diffs[old_key] = {'previous': expected, 'recomputed': got}
        if diffs:
            raise ValueError('SQLite-based counts fail to reproduce chained report: '
                             + ','.join(sorted(diffs)))
    broad = widest.copy()
    broad['index_year'] = broad['index_date'].str[:4]
    broad['age_band'] = pd.cut(broad['age'], bins=[18, 29, 39, 50],
                               labels=['19-29', '30-39', '40-50'], include_lowest=True)
    if broad['age_band'].isna().any():
        raise ValueError('Unexpected age grouping')
    timing = {}
    for mod in MODALITIES:
        sub = joined.loc[joined['modality'].eq(mod)]
        timing[mod] = {
            'on_index_day_unique_patients': int(sub.loc[sub['offset_days'].eq(0), 'patient_id'].nunique()),
            'before_index_unique_patients': int(sub.loc[sub['offset_days'].lt(0), 'patient_id'].nunique()),
            'after_index_unique_patients': int(sub.loc[sub['offset_days'].gt(0), 'patient_id'].nunique()),
        }
    return {
        'stage': 'STEP22_LOCAL_SQLITE_VALIDATION_ONLY',
        'complete_index_required': True,
        'reprocessed_zip_records': 0,
        'age_eligible_n': int(len(cohort)),
        'matched_distinct_modality_days': int(len(joined)),
        'windows_inclusive_days_each_side': window_reports,
        'previous_chained_report_compared': prior is not None,
        'previous_chained_report_discrepancies': diffs,
        'race_unknown_or_missing_n': int(is_unknown(cohort['race']).sum()),
        'ethnicity_unknown_or_missing_n': int(is_unknown(cohort['ethnicity']).sum()),
        'boundary_age_19_n': int(cohort['age'].eq(19).sum()),
        'boundary_age_50_n': int(cohort['age'].eq(50).sum()),
        'by_index_year': group_summary(broad, ['index_year']),
        'by_sex': group_summary(broad, ['sex']),
        'by_age_band': group_summary(broad, ['age_band']),
        'by_year_and_sex': group_summary(broad, ['index_year', 'sex']),
        'temporal_direction_unique_patients': timing,
        'study_inference_allowed': False,
        'limitations': [
            'No encounter IDs: dates are not admissions or encounter-validated linkage.',
            'These CPTs are the historical nine-code list and may undercount clinical imaging.',
            'Index defined by 2018-2019 principal I63 diagnosis, without pre-2018 lookback.',
            'Approximate age uses index calendar year minus birth year.',
            'Overlapping pre-, same-day and post-index categories are not mutually exclusive.',
            'Subgroups with small cells are withheld, not presented as zero.',
            'Do not use this provisional cohort for population rates, disparities or manuscript modeling.',
        ],
    }


def run(private_dir: Path, prior_summary: Path | None = None) -> dict:
    root = private_dir.expanduser().resolve()
    if not root.is_dir() or ROOT.resolve() in root.parents or root == ROOT.resolve():
        raise ValueError('Private directory must exist outside Git repository')
    if stat.S_IMODE(root.stat().st_mode) & 0o077:
        raise ValueError('Private directory must have owner-only permissions')
    expected = root / 'source_signature.json'
    if not expected.is_file():
        raise ValueError('Missing archive signature from chained reconstruction')
    d = read_complete_db(root / DX_NAME, 'first_principal_I63',
                         'patient_id,index_date,dx_code')
    e = read_complete_db(root / COHORT_NAME, 'eligible',
                         'patient_id,index_date,sex,age,race,ethnicity')
    i = read_complete_db(root / IMAGING_NAME, 'imaging_event',
                         'patient_id,modality,procedure_date')
    if not set(e['patient_id']).issubset(set(d['patient_id'])):
        raise ValueError('Demographic cohort has IDs absent from complete diagnosis index')
    # Explicitly check chosen index dates match earlier diagnosis stage.
    check = e[['patient_id', 'index_date']].merge(
        d[['patient_id', 'index_date']], how='left', on='patient_id',
        validate='one_to_one', suffixes=('_cohort', '_diagnosis'))
    if not check['index_date_cohort'].eq(check['index_date_diagnosis']).all():
        raise ValueError('Index dates disagree between complete stages')
    prior = None
    if prior_summary is not None:
        prior = json.loads(prior_summary.read_text(encoding='utf-8'))
        if prior.get('completed_all_source_scans') is not True:
            raise ValueError('Prior report is not a full completed scan')
    report = evaluate(e, i, prior)
    report['full_diagnosis_index_patients'] = int(len(d))
    report['private_databases_source_verified_by_manifest_previous_stage'] = True
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--private-dir', required=True, type=Path)
    p.add_argument('--compare-audit', type=Path, default=None)
    p.add_argument('--output', type=Path,
                   default=ROOT / 'results/phase1/step22_temporal_qc.json')
    args = p.parse_args()
    report = run(args.private_dir, args.compare_audit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n',
                           encoding='utf-8')
    print('Step 22 aggregate report:', args.output)
    print('Previously scanned ZIP rows reused; no ZIP extraction or scan.')
    print('Study inference remains BLOCKED without encounter and codebook validation.')


if __name__ == '__main__':
    main()
