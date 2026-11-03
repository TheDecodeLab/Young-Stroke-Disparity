#!/usr/bin/env python3
"""Validate recorded CPT-code P-standardization from an existing private aggregate.

Reads ONLY Step78 table3_year_quarantine.csv. No raw patient data or SQLite scans.
Full cell details stay local. No clinical-disparity claims or HCO-cluster CIs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (ROOT / 'results/phase1/full_reconstruction_private/'
                 'step78_paper_exhibits_private/draft_v1/table3_year_quarantine.csv')
DEFAULT_OUTPUT = (ROOT / 'results/phase1/full_reconstruction_private/'
                  'step87_s3_aggregate_private/s3_sensitivity_INTERNAL_ONLY.json')
ACK = 'I_CONFIRM_INTERNAL_REVIEW_ONLY'
YEARS = tuple(str(y) for y in range(2016, 2025))
GROUPS = ('NONE', 'ANY_AMBIG')
FIELDS = ('index_inpatient_pct', 'index_or_other_day0_pct')
THRESHOLDS = (11, 30, 50, 100, 200, 300)


def parse_int(s: str) -> int:
    n = int(s)
    if n < 1:
        raise ValueError('Missing or nonpositive aggregate denominator')
    return n


def parse_aggregate(path: Path):
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError('Only a regular restricted input CSV is allowed')
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        expected = {'year','P_indicator','any_ambiguous_group','cell_suppressed',
                    'denominator',*FIELDS}
        if set(reader.fieldnames or ()) != expected:
            raise ValueError('Unexpected Step78 aggregate columns')
        rows = list(reader)
    if len(rows) != 4*(len(YEARS)+1):
        raise ValueError('Expected four P x ambiguity rows per year, plus ALL')
    output = {}
    for r in rows:
        y,held,p = r['year'],r['any_ambiguous_group'],r['P_indicator']
        if y not in (*YEARS,'ALL') or held not in GROUPS or p not in ('0','1'):
            raise ValueError('Unsupported grouping value')
        if str(r['cell_suppressed']).strip().lower() not in ('false','0'):
            raise ValueError('Suppressed stratum cannot support exact sensitivity')
        key = (y,held,int(p))
        if key in output:
            raise ValueError('Duplicate stratum')
        n = parse_int(r['denominator'])
        rec = {'n': n}
        for f in FIELDS:
            percent = float(r[f])
            if not math.isfinite(percent) or not 0 <= percent <= 100:
                raise ValueError('Invalid code-capture percentage')
            k_f = percent*n/100
            k = round(k_f)
            if abs(k-k_f) > 1e-5 or not 0 <= k <= n:
                raise ValueError('Event percentage does not reconstruct a patient count')
            rec[f] = k
        if rec[FIELDS[0]] > rec[FIELDS[1]]:
            raise ValueError('Nested code-presence indicators fail')
        output[key] = rec
    if len(output) != 4*(len(YEARS)+1):
        raise ValueError('Incomplete aggregate partition')
    for p in (0,1):
        for held in GROUPS:
            all_row = output[('ALL',held,p)]
            for field in ('n',*FIELDS):
                if all_row[field] != sum(output[(year,held,p)][field] for year in YEARS):
                    raise ValueError('Annual totals fail ALL-group reconciliation')
    return output


def summarize_group(rows, field, years=YEARS, ambiguities=GROUPS, minimum=1):
    """Common weights only for included strata. Restrictions alter target mix."""
    strata = []
    for year in years:
        for held in ambiguities:
            a, b = rows[(year,held,0)], rows[(year,held,1)]
            if min(a['n'],b['n']) >= minimum:
                strata.append((a,b))
    total_n = sum(a['n']+b['n'] for a,b in strata)
    if not total_n:
        return {'available': False, 'n': 0}
    p0 = sum((a['n']+b['n'])*a[field]/a['n'] for a,b in strata)/total_n
    p1 = sum((a['n']+b['n'])*b[field]/b['n'] for a,b in strata)/total_n
    return {'available': True, 'n':total_n, 'strata':len(strata),
            'P0_pct':100*p0,'P1_pct':100*p1,'P1_minus_P0_pp':100*(p1-p0)}


def crude(rows,field):
    totals=[]
    for p in (0,1):
        n=sum(rows[('ALL',h,p)]['n'] for h in GROUPS)
        k=sum(rows[('ALL',h,p)][field] for h in GROUPS)
        totals.append(100*k/n)
    return {'P0_pct':totals[0],'P1_pct':totals[1],
            'P1_minus_P0_pp':totals[1]-totals[0]}


def era_pooled(rows, field):
    weights=[]
    for era in (YEARS[0:3],YEARS[3:6],YEARS[6:9]):
        for h in GROUPS:
            n=[sum(rows[(y,h,p)]['n'] for y in era) for p in (0,1)]
            k=[sum(rows[(y,h,p)][field] for y in era) for p in (0,1)]
            weights.append((n[0]+n[1], k[0]/n[0], k[1]/n[1]))
    N=sum(t[0] for t in weights)
    return {'P1_minus_P0_pp':100*sum(n*(p1-p0) for n,p0,p1 in weights)/N,
            'pooled_periods':3,'joint_strata':len(weights)}


def year_only(rows, field):
    nums=[]
    for y in YEARS:
        n=[sum(rows[(y,h,p)]['n'] for h in GROUPS) for p in (0,1)]
        k=[sum(rows[(y,h,p)][field] for h in GROUPS) for p in (0,1)]
        nums.append((sum(n),k[0]/n[0],k[1]/n[1]))
    N=sum(z[0] for z in nums)
    return 100*sum(w*(p1-p0) for w,p0,p1 in nums)/N


def analyze(rows):
    sizes=[rows[(y,h,p)]['n'] for y in YEARS for h in GROUPS for p in (0,1)]
    totals=[sum(rows[('ALL',h,p)]['n'] for h in GROUPS) for p in (0,1)]
    N=sum(totals)
    result={
        'scope': 'private_aggregate_reconciliation_only',
        'indexed_patients':N,'P0':totals[0],'P1':totals[1],
        'years':list(YEARS),'joint_strata':len(YEARS)*len(GROUPS),
        'joint_stratum_P_cells':len(sizes),
        'min_P_cell_n':min(sizes),
        'min_same_day_events': min(rows[(y,h,p)][FIELDS[1]] for y in YEARS for h in GROUPS for p in (0,1)),
        'min_same_day_complements': min(rows[(y,h,p)]['n']-rows[(y,h,p)][FIELDS[1]] for y in YEARS for h in GROUPS for p in (0,1)),
        'outcomes':{},
    }
    for field in FIELDS:
        full = summarize_group(rows,field)
        thresholded = {}
        for threshold in THRESHOLDS:
            cell = summarize_group(rows,field,minimum=threshold)
            cell['retained_pct'] = 100*cell['n']/N
            cell['excluded_strata'] = len(YEARS)*len(GROUPS)-(cell.get('strata') or 0)
            thresholded[str(threshold)] = cell
        loo = {year:summarize_group(rows,field,years=tuple(z for z in YEARS if z!=year))
               for year in YEARS}
        within = {held:summarize_group(rows,field,ambiguities=(held,)) for held in GROUPS}
        result['outcomes'][field] = {
            'crude':crude(rows,field),
            'full':full,'year_only_pp':year_only(rows,field),
            'leave_one_year_out':loo,
            'loo_range_pp': [min(x['P1_minus_P0_pp'] for x in loo.values()),
                              max(x['P1_minus_P0_pp'] for x in loo.values())],
            'pooled_three_year_eras':era_pooled(rows,field),
            'thresholded':thresholded,
            'year_standardized_by_ambiguity':within,
            'loo_sign_consistent':all(x['P1_minus_P0_pp']*full['P1_minus_P0_pp']>0
                                      for x in loo.values()),
        }
    if sum(rows[(y,h,p)]['n'] for y in YEARS for h in GROUPS for p in (0,1))!=N:
        raise ValueError('Annual strata fail global total')
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--csv',type=Path,default=DEFAULT_INPUT)
    ap.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    ap.add_argument('--acknowledge',required=True)
    args=ap.parse_args()
    if args.acknowledge != ACK:
        ap.error('Local-only research review acknowledgement required')
    private=(ROOT/'results/phase1/full_reconstruction_private').resolve()
    if private not in args.output.resolve().parents:
        raise ValueError('Output must remain in private, gitignored research results')
    if args.output.is_symlink() or args.output.exists():
        raise FileExistsError('Refusing to overwrite existing report')
    input_bytes=args.csv.read_bytes()
    result=analyze(parse_aggregate(args.csv))
    result['source_sha256']=hashlib.sha256(input_bytes).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(args.output.parent,0o700)
    fd=os.open(args.output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w',encoding='utf8') as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write('\n')
    print('Step87 aggregate integrity: PASS')
    print('Strata available:',result['joint_strata'])
    print('Joint P cells >=200:',result['min_P_cell_n']>=200)
    print('Leave-one-year-out same-day sign consistent:',
          result['outcomes'][FIELDS[1]]['loo_sign_consistent'])
    print('Restricted report:',args.output)
    print('Do not publish source-specific cell counts from this report without review.')

if __name__=='__main__':
    main()