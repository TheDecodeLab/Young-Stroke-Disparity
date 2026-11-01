"""Synthetic tests for the private Step78 stratification audit."""
import csv
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1]/'scripts/step87_s3_aggregate_sensitivity.py'
spec=importlib.util.spec_from_file_location('step87_s3',PATH)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fake_csv(path, bad=None):
    rows=[]
    for y in ('ALL',*m.YEARS):
        for h in m.GROUPS:
            for p in (0,1):
                n=9*900 if y=='ALL' else 900
                r={'year':y,'P_indicator':p,'any_ambiguous_group':h,
                   'cell_suppressed':'False','denominator':n,
                   'index_inpatient_pct':100*(200+50*p)/900,
                   'index_or_other_day0_pct':100*(400+50*p)/900}
                rows.append(r)
    if bad:bad(rows)
    with path.open('w',newline='') as f:
        out=csv.DictWriter(f,fieldnames=list(rows[0]))
        out.writeheader();out.writerows(rows)


def test_reconstructs_aggregate_and_stability(tmp_path):
    path=tmp_path/'f.csv';fake_csv(path)
    rows=m.parse_aggregate(path);a=m.analyze(rows)
    assert a['joint_strata']==18
    assert a['min_P_cell_n']==900
    assert a['outcomes']['index_or_other_day0_pct']['loo_sign_consistent']
    assert a['outcomes']['index_or_other_day0_pct']['full']['strata']==18
    assert a['outcomes']['index_or_other_day0_pct']['thresholded']['300']['retained_pct']==100
    assert a['outcomes']['index_or_other_day0_pct']['full']['P1_minus_P0_pp']>0


def test_suppression_fails(tmp_path):
    path=tmp_path/'f.csv';fake_csv(path,lambda rows:rows[6].update(cell_suppressed='True'))
    with pytest.raises(ValueError,match='Suppressed'):m.parse_aggregate(path)


def test_missing_partition_fails(tmp_path):
    path=tmp_path/'f.csv';fake_csv(path,lambda rows:rows[4].update(year='2017'))
    with pytest.raises(ValueError):m.parse_aggregate(path)


def test_noninteger_rounding_fails(tmp_path):
    path=tmp_path/'f.csv';fake_csv(path,lambda rows:rows[4].update(index_inpatient_pct='32.123'))
    with pytest.raises(ValueError,match='reconstruct'):m.parse_aggregate(path)


def test_annual_total_fails(tmp_path):
    path=tmp_path/'f.csv';fake_csv(path,lambda rows:rows[0].update(denominator='90'))
    with pytest.raises(ValueError,match='Annual totals'):m.parse_aggregate(path)


def test_nested_endpoint_fails(tmp_path):
    path=tmp_path/'f.csv';fake_csv(path,lambda rows:rows[4].update(index_or_other_day0_pct='0.0'))
    with pytest.raises(ValueError,match='Nested'):m.parse_aggregate(path)