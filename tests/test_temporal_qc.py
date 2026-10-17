"""Only synthetic dates, IDs, and events are used in these tests."""
import pandas as pd
import pytest
from scripts.step22_temporal_qc import evaluate, verify_index, group_summary


def mini():
    c = pd.DataFrame([
        ('a','20180101','Female',40,'Unknown','Unknown'),
        ('b','20180701','Male',21,'Unknown','Unknown'),
        ('c','20190101','Female',30,'Unknown','Unknown'),
        ('d','20181231','Male',45,'Unknown','Unknown'),
        ('e','20180401','Female',48,'Unknown','Unknown'),
    ],columns=['patient_id','index_date','sex','age','race','ethnicity'])
    ev = pd.DataFrame([
        ('a','CT','20180101'), ('a','MRI','20180105'),
        ('b','CT','20180701'), ('c','CTA','20190102'),
    ],columns=['patient_id','modality','procedure_date'])
    return c,ev


def test_window_and_old_reconciliation():
    c,ev=mini()
    old={'stages':[{'none':1},{'aggregate_cohort_integrity':{
      'age_eligible_first_diagnosis_n':5,'ct_n':2,'mri_n':1,
      'cta_n':1,'mra_n':0,'ct_only_n':1,'ct_and_additional_n':1,
      'advanced_no_ct_n':1,'none_of_four_imaging_n':2}}]}
    rep=evaluate(c,ev,old)
    assert rep['previous_chained_report_compared']
    assert rep['previous_chained_report_discrepancies']=={}
    assert rep['windows_inclusive_days_each_side']['7']['CT only']==1
    assert rep['windows_inclusive_days_each_side']['0']['CT only']==2
    assert rep['windows_inclusive_days_each_side']['0']['None of four']==3
    assert rep['windows_inclusive_days_each_side']['7']['None of four']==2
    assert rep['race_unknown_or_missing_n']==5
    assert rep['temporal_direction_unique_patients']['MRI']['after_index_unique_patients']==1
    assert rep['matched_distinct_modality_days']==4
    assert rep['study_inference_allowed'] is False
    assert rep['by_sex'][0]['suppressed']


def test_missing_patient_in_events_rejected():
    c,ev=mini()
    ev.loc[0,'patient_id']='outsider'
    with pytest.raises(ValueError,match='noneligible'):
        evaluate(c,ev)


def test_invalid_event_window_rejected():
    c,ev=mini()
    ev.loc[0,'procedure_date']='20180201'
    with pytest.raises(ValueError,match='outside'):
        evaluate(c,ev)


def test_duplicate_index_rejected():
    c,ev=mini()
    with pytest.raises(ValueError,match='duplicated'):
        verify_index(pd.concat([c,c.iloc[:1]]),ev)


def test_small_strata_do_not_leak_counts():
    c,ev=mini()
    from scripts.step22_temporal_qc import classify
    e=verify_index(c,ev)
    f=classify(c,e,7)
    x=group_summary(f,['sex'])
    assert all(o=={'stratum':o['stratum'],'suppressed':True} for o in x)


def test_reconciliation_fails_on_mismatch():
    c,ev=mini()
    prior={'stages':[{'aggregate_cohort_integrity':{
      'age_eligible_first_diagnosis_n':6,'ct_n':2,'mri_n':1,
      'cta_n':1,'mra_n':0,'ct_only_n':1,'ct_and_additional_n':1,
      'advanced_no_ct_n':1,'none_of_four_imaging_n':2}}]}
    with pytest.raises(ValueError,match='fail to reproduce'):
        evaluate(c,ev,prior)


def test_out_of_range_age_rejected():
    c,ev=mini()
    c.loc[0,'age']=17
    with pytest.raises(ValueError,match='outside 19-50'):
        evaluate(c,ev)


def test_read_only_full_stage_sqlite(tmp_path):
    import sqlite3
    import os
    import json
    from scripts.step22_temporal_qc import run
    from pathlib import Path
    work=tmp_path/'private'
    for name in ('diagnosis','demographics','imaging'):
        (work/name).mkdir(parents=True)
    work.chmod(0o700)
    (work/'source_signature.json').write_text(json.dumps({'archive_members_sha256':'synthetic'}))
    files = {
        'diagnosis/step18_diagnosis_index.sqlite':
            ('first_principal_I63', 'patient_id TEXT PRIMARY KEY,index_date TEXT,dx_code TEXT',
             [('a','20180101','I63.9'),('b','20180701','I63.9'),('c','20190101','I63.9')]),
        'demographics/step19_age_cohort.sqlite':
            ('eligible','patient_id TEXT PRIMARY KEY,index_date TEXT,sex TEXT,age INTEGER,race TEXT,ethnicity TEXT',
             [('a','20180101','Female',40,'Unknown','Unknown'),
              ('b','20180701','Male',21,'Unknown','Unknown'),
              ('c','20190101','Female',30,'Unknown','Unknown')]),
        'imaging/step20_imaging_events.sqlite':
            ('imaging_event','patient_id TEXT,modality TEXT,procedure_date TEXT',
             [('a','CT','20180101'),('b','CTA','20180701')]),
    }
    for path,(tbl,cols,rows) in files.items():
        with sqlite3.connect(work/path) as con:
            con.execute(f'CREATE TABLE {tbl} ({cols})')
            con.execute('CREATE TABLE scan_state (key TEXT,value TEXT)')
            con.execute("INSERT INTO scan_state VALUES ('scan_complete','1')")
            con.executemany('INSERT INTO '+tbl+' VALUES ('+','.join(['?']*len(rows[0]))+')', rows)
    r=run(work)
    assert r['full_diagnosis_index_patients']==3
    assert r['windows_inclusive_days_each_side']['7']['CT']==1
    assert r['windows_inclusive_days_each_side']['7']['CTA']==1
    assert r['reprocessed_zip_records']==0
    with sqlite3.connect(work/'imaging/step20_imaging_events.sqlite') as con:
        con.execute("UPDATE scan_state SET value='0' WHERE key='scan_complete'")
    with pytest.raises(ValueError,match='not marked complete'):
        run(work)
