"""Step79 synthetic-only cross-table arithmetic and release-gate checks."""
import csv
import json
from collections import Counter,defaultdict
from itertools import product
from copy import deepcopy

import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step78_paper_results_bundle as s78
from scripts import step79_manuscript_exhibit_integrity as s79


def make_tables():
    counts=defaultdict(Counter)
    for cohort in s62.COHORTS:
        for year,p,held in product(("2020","2021"),(0,1),(0,1)):
            # Keep synthetic Table3 numerators and complements >=11;
            # separate tests deliberately insert small disclosure risks.
            patch=Counter(
                n=50,inpatient=20+4*p+2*(year=="2021")+held,
                new_other_day0=8+3*p+held,new_ed=3+p,
                union_ed_or_pre2_day0=13+4*p+held)
            q="ANY_AMBIG" if held else "NONE"
            for key in (
                ("COHORT",cohort),
                ("P",cohort+"|P="+str(p)),
                ("QUARANTINE_P",cohort+"|P="+str(p)+"|"+q),
                ("YEAR_P",cohort+"|"+year+"|P="+str(p)),
                ("YEAR_QUARANTINE_P",cohort+"|"+year+"|P="+str(p)+"|"+q)
            ):
                counts[key].update(patch)
    t1=s78.source_counts(counts)
    t2=s78.endpoint_rows(counts)
    t3=s78.quality_rows(counts)
    t4=[]
    for dim,cats in (
        ("sex",("FEMALE","MALE")),
        ("race",("WHITE","UNKNOWN_MISSING")),
        ("ethnicity",("HISPANIC_LATINO","NOT_HISPANIC_LATINO"))
    ):
        for cat in cats:
            t4.append(dict(dimension=dim,category=cat,suppressed=False,
                           n=200,share_pct=50.,P1_pct=50.,
                           index_inpatient_documented_pct=25.,
                           same_day_encounter_documented_pct=36.,
                           missing_or_unmapped=cat=="UNKNOWN_MISSING"))
    t5=[]
    for outcome in ("imp_any","same_day_any"):
        for field,ref,alternative in s78.s73.TARGETS:
            t5.append(dict(endpoint=outcome,dimension=field,
                           reference=ref,comparison=alternative,
                           comparison_n=100,reference_n=100,
                           marginal_reference_pct=35.,
                           marginal_comparison_pct=33.,
                           marginal_difference_pp=-2.,
                           extra_binomial_sensitivity_low_pp=-4.,
                           extra_binomial_sensitivity_high_pp=0.,
                           HCO_cluster_corrected=False,
                           case_mix_severity_corrected=False,
                           not_confirmed_care_disparity=True))
    return dict(t1=t1,t2=t2,t3=t3,t4=t4,t5=t5),counts


def test_internal_cross_table_numeric_reconciliation():
    tables,_=make_tables()
    assert s79.audit(tables)==[]


def test_fails_if_table2_denominator_disagrees():
    tables,_=make_tables()
    bad=deepcopy(tables)
    bad["t2"][0]["P0_n"]+=1
    with pytest.raises(ValueError,match="denominators disagree"):
        s79.audit(bad)


def test_fails_if_main_inpatient_baseline_disagrees():
    tables,_=make_tables()
    bad=deepcopy(tables)
    row=next(x for x in bad["t2"] if x["cohort"]==s78.PRIMARY
             and x["endpoint_key"]=="INDEX_IMP")
    row["P0_documented_code_n"]+=1
    row["P0_crude_pct"]=100*row["P0_documented_code_n"]/row["P0_n"]
    row["P1_minus_P0_crude_pp"]=row["P1_crude_pct"]-row["P0_crude_pct"]
    with pytest.raises(ValueError,match="baseline disagrees"):
        s79.audit(bad)


def test_small_increment_complement_and_secondary_suppression_risks():
    tables,_=make_tables()
    bad=deepcopy(tables)
    base=next(x for x in bad["t2"] if x["cohort"]==s78.PRIMARY
              and x["endpoint_key"]=="INDEX_IMP")
    row=next(x for x in bad["t2"] if x["cohort"]==s78.PRIMARY
             and x["endpoint_key"]=="INDEX_IMP_OR_UNIQUE_ED")
    row["P0_documented_code_n"]=base["P0_documented_code_n"]+5
    row["P0_crude_pct"]=100*row["P0_documented_code_n"]/row["P0_n"]
    row["P1_minus_P0_crude_pp"]=row["P1_crude_pct"]-row["P0_crude_pct"]
    flags=s79.audit(bad)
    assert "small_added_code_increment_between_public_tables" in flags
    qu=deepcopy(tables)
    q=next(x for x in qu["t3"] if x["year"]=="2020"
           and x["P_indicator"]==1 and
           x["any_ambiguous_group"]=="NONE")
    q.update(cell_suppressed=True,denominator=None,index_inpatient_pct=None,
             index_or_other_day0_pct=None)
    assert "Table3_suppressed_cells_require_secondary_suppression" in (
        s79.audit(qu))


def test_false_clinical_and_cluster_claims_do_not_pass():
    tables,_=make_tables()
    bad=deepcopy(tables)
    bad["t5"][0]["HCO_cluster_corrected"]=True
    with pytest.raises(ValueError,match="overstates model validity"):
        s79.audit(bad)


def test_draft_inventory_and_manifest_validation(tmp_path):
    tables,counts=make_tables()
    folder=tmp_path/"draft_v1"
    folder.mkdir()
    for key,name in s79.TABLES.items():
        s78.write_csv(folder/name,tables[key])
    s78.plots(tables["t2"],folder)
    (folder/"RESULTS_DRAFT_LOCAL_ONLY.md").write_text(
        s78.narrative(counts,tables["t2"],tables["t4"],tables["t5"]),
        encoding="utf8")
    manifest=dict(policy=s78.POLICY,primary_cohort=s78.PRIMARY,
                  disclosure_review_required=True,
                  historical_cohort_overlaps_primary=True,
                  reported_p_is_unvalidated_principal_I63_flag=True,
                  manuscript_ready_for_public_release=False,
                  performed_imaging_verified=False,
                  hospital_cluster_inference_available=False,
                  exhibits=sorted(s79.BUNDLE-{"manifest_LOCAL_ONLY.json"}))
    (folder/"manifest_LOCAL_ONLY.json").write_text(
        json.dumps(manifest),encoding="utf8")
    decoded,metadata,draft=s79.read_private_bundle(folder)
    assert s79.audit(decoded)==[]
    assert metadata["policy"]==s78.POLICY
    assert "scan completion" in draft
    manifest["performed_imaging_verified"]=True
    (folder/"manifest_LOCAL_ONLY.json").write_text(
        json.dumps(manifest),encoding="utf8")
    with pytest.raises(ValueError,match="incorrectly marked available"):
        s79.read_private_bundle(folder)
