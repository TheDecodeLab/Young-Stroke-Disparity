"""Step78 synthetic-only final-results reproducibility / disclosure tests."""
from collections import Counter,defaultdict
from itertools import product
from math import exp
from pathlib import Path
import csv

import numpy as np
import pandas as pd
import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step78_paper_results_bundle as s78


def fabricated_counts():
    counts=defaultdict(Counter)
    for cohort in s62.COHORTS:
        for year,P,held in product(("2020","2021"),(0,1),(0,1)):
            n=50
            imp=10+4*P+2*(year=="2021")+held
            day0=8+3*P+held
            ed=3+P
            prec=5+P
            patch=Counter(
                n=n,
                inpatient=imp,
                new_other_day0=day0,
                new_ed=ed,
                union_ed_or_pre2_day0=day0+prec,
            )
            lab="ANY_AMBIG" if held else "NONE"
            keys=(
                ("COHORT",cohort),
                ("P",cohort+"|P="+str(P)),
                ("QUARANTINE_P",cohort+"|P="+str(P)+"|"+lab),
                ("YEAR_P",cohort+"|"+year+"|P="+str(P)),
                ("YEAR_QUARANTINE_P",cohort+"|"+year+"|P="+str(P)+"|"+lab)
            )
            for k in keys:
                counts[k].update(patch)
    return counts


def fabricated_model_table():
    rows=[]
    for cohort,year,age,sex,race,eth,P,held in product(
            s62.COHORTS,("2018","2024"),("25TO34","35TO44"),
            ("MALE","FEMALE"),
            ("WHITE","BLACK_AFRICAN_AMERICAN","ASIAN","AIAN","NHPI",
             "UNKNOWN_MISSING"),("NOT_HISPANIC_LATINO","HISPANIC_LATINO"),
            (0,1),(0,1)):
        scale=(-0.4 + .1*(sex=="FEMALE")-.18*(race=="ASIAN")
               -.1*(race=="AIAN")-.15*(race=="NHPI")
               +.04*(eth=="HISPANIC_LATINO")+.15*P+.06*held)
        n=60
        imp=int(round(n/(1+exp(-scale))))
        rows.append({"cohort":cohort,"year":year,"age_band":age,
                     "sex":sex,"race":race,"ethnicity":eth,
                     "P":P,"held":held,"n":n,
                     "imp_any":imp,"same_day_any":min(imp+8,n)})
    return pd.DataFrame(rows)


def test_primary_counts_and_quarantine_reconcile():
    c=fabricated_counts()
    rows=s78.source_counts(c)
    assert len(rows)==len(s62.COHORTS)*2
    p1=next(r for r in rows if r["cohort"]==s78.PRIMARY
            and r["P_indicator"]==1)
    assert p1["denominator"]==200
    assert p1["any_ambiguous_encounter_patient_n"]==100
    assert p1["index_inpatient_CPT14_n"]==62
    assert p1["index_inpatient_CPT14_pct"]==pytest.approx(31)


def test_prespecified_endpoints_and_common_quality_weighting():
    c=fabricated_counts()
    rows=s78.endpoint_rows(c)
    assert len(rows)==len(s62.COHORTS)*4
    primary=[x for x in rows if x["cohort"]==s78.PRIMARY]
    assert [x["endpoint_key"] for x in primary]==[e[0] for e in s78.ENDPOINTS]
    base=primary[0]
    day=primary[1]
    assert base["P0_n"]==base["P1_n"]==200
    assert base["P0_documented_code_n"]==46
    assert base["P1_documented_code_n"]==62
    assert base["P1_minus_P0_crude_pp"]==pytest.approx(8)
    assert base["P1_minus_P0_common_year_quarantine_pp"]==pytest.approx(8)
    assert day["P1_documented_code_n"]==62+46
    assert day["P0_documented_code_n"]==46+34
    assert day["P1_minus_P0_crude_pp"]==pytest.approx(14)
    assert day["P1_minus_P0_common_year_quarantine_pp"]==pytest.approx(14)
    assert day["P1_minus_P0_no_ambiguous_pp"]==pytest.approx(14)
    assert all(not row["actual_imaging_performed_verified"] for row in rows)
    assert all(not row["HCO_episode_verified"] for row in rows)


def test_quality_rows_small_cells_and_no_source_identifiers():
    c=fabricated_counts()
    q=s78.quality_rows(c)
    assert len(q)==2*2*(2+1) # ALL and 2 years, P x held
    assert all(row["denominator"]==50 or row["denominator"]==100
               for row in q)
    assert all(row["cell_suppressed"] is False for row in q)
    assert all("patient" not in row and "encounter" not in row
               for row in q)
    c[("YEAR_QUARANTINE_P",s78.PRIMARY+"|2021|P=1|ANY_AMBIG")]=Counter(
        n=5,inpatient=1,new_other_day0=1)
    q=s78.quality_rows(c)
    tiny=next(r for r in q if r["year"]=="2021"
              and r["P_indicator"]==1
              and r["any_ambiguous_group"]=="ANY_AMBIG")
    assert tiny["cell_suppressed"] is True
    assert tiny["denominator"] is None
    assert tiny["index_or_other_day0_pct"] is None


def test_demo_missingness_and_point_estimates_are_separate():
    tab=fabricated_model_table()
    rows=s78.demographic_rows(tab)
    race={r["category"]:r for r in rows if r["dimension"]=="race"}
    assert race["UNKNOWN_MISSING"]["missing_or_unmapped"] is True
    assert race["WHITE"]["missing_or_unmapped"] is False
    assert race["WHITE"]["n"]>11
    assert len(rows)>10


def test_model_outputs_explicitly_nonclinical_and_nonclustered():
    tab=fabricated_model_table()
    rows=s78.exploratory_models(tab)
    assert len(rows)==2*len(s78.s73.TARGETS)
    for row in rows:
        assert row["HCO_cluster_corrected"] is False
        assert row["not_confirmed_care_disparity"] is True
        assert row["extra_binomial_sensitivity_low_pp"] <= (
            row["marginal_difference_pp"]) <= (
            row["extra_binomial_sensitivity_high_pp"])
        assert np.isfinite(row["marginal_difference_pp"])


def test_results_narrative_and_private_csv(tmp_path):
    c=fabricated_counts()
    d=s78.endpoint_rows(c)
    tab=fabricated_model_table()
    demos=s78.demographic_rows(tab)
    text=s78.narrative(c,d,demos,[])
    assert "NOT publication- or external-disclosure-ready" in text
    assert "documented" in text
    assert "same HCO" in text
    assert "scan completion" in text
    assert "confirmed" not in text.lower().replace(
        "not confirmed","")
    fp=tmp_path/"synthetic.csv"
    s78.write_csv(fp,s78.source_counts(c))
    with fp.open(encoding="utf8",newline="") as handle:
        x=list(csv.DictReader(handle))
    assert len(x)==len(s62.COHORTS)*2


def test_plot_files_are_local_only_and_do_not_change_data(tmp_path):
    src=s78.endpoint_rows(fabricated_counts())
    s78.plots(src,tmp_path)
    for name in ("figure1_coded_capture_by_encounter.png",
                 "figure2_source_quality_standardization.png"):
        p=tmp_path/name
        assert p.exists() and p.stat().st_size>1200
    assert s78.endpoint_rows(fabricated_counts())==src
