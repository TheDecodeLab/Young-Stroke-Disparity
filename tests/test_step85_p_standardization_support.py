"""Synthetic-only tests for Step85; no TriNetX datasets or local clinical files."""
from collections import Counter
from copy import deepcopy

import pytest

from scripts import step85_p_standardization_support as s85

COHORT="uniform_18_50"

class FakeStep70:
    @staticmethod
    def strata(counts,cohort,kind):
        assert kind=="year_and_quarantine"
        out={}
        for (label,key),row in counts.items():
            if label!="YEAR_QUARANTINE_P" or not key.startswith(cohort+"|"):
                continue
            year,p,held=key[len(cohort)+1:].split("|")
            out.setdefault((year,held),{})[int(p[-1])]=row
        return out
    @classmethod
    def standardized(cls,counts,cohort,fields,kind):
        strata=cls.strata(counts,cohort,kind)
        n=sum(sum(v["n"] for v in m.values()) for m in strata.values())
        probs=[0.0,0.0]
        for cells in strata.values():
            w=sum(c["n"] for c in cells.values())/n
            for p in (0,1):
                probs[p]+=w*sum(cells[p].get(k,0) for k in fields)/cells[p]["n"]
        return (100*probs[0],100*probs[1],100*(probs[1]-probs[0]))

def fixture_counts():
    c={("COHORT",COHORT):{"n":18000}}
    for i in range(18):
        year=str(2016+i//2)
        held="NONE" if i%2==0 else "ANY_AMBIG"
        for p,n_total,rate in ((0,12000,.56635),(1,6000,.5298)):
            n=n_total//18+(i<n_total%18)
            imp=round(n*.2)
            day=round(n*rate)-imp
            c[("YEAR_QUARANTINE_P",COHORT+"|"+year+"|P="+str(p)+"|"+held)]=Counter(
                {"n":n,"inpatient":imp,"new_other_day0":day})
    return c

def test_accurate_synthetic_standardization_and_sensitivities():
    report=s85.summarize(fixture_counts(),COHORT,FakeStep70)
    assert report["n_indexed"]==18000
    assert len(report["strata"])==18
    assert all(report["thresholds"][str(t)]["all_strata_adequate"] for t in s85.THRESHOLDS)
    assert report["metrics"]["same_day"]["full"]["P1_minus_P0_pp"]<0
    assert report["metrics"]["same_day"]["all_loo_same_sign"]
    assert report["metrics"]["same_day"]["pooled_three_year_era"]["available"]
    assert report["metrics"]["same_day"]["thresholded"]["100"]["coverage"]==1

def test_insufficient_stratum_is_detected_without_fabricated_imputation():
    counts=fixture_counts()
    k0=("YEAR_QUARANTINE_P",COHORT+"|2016|P=0|NONE")
    k1=("YEAR_QUARANTINE_P",COHORT+"|2016|P=0|ANY_AMBIG")
    move=counts[k0]["n"]-5
    counts[k0]["n"]=5
    counts[k0]["inpatient"]=1
    counts[k0]["new_other_day0"]=2
    counts[k1]["n"]+=move
    counts[k1]["inpatient"]+=int(move*.2)
    counts[k1]["new_other_day0"]+=int(move*.36)
    grouped=FakeStep70.strata(counts,COHORT,"year_and_quarantine")
    assert s85._weighted(grouped,("inpatient","new_other_day0"),11)["coverage"]<1
    assert any(min(c[0]["n"],c[1]["n"])<11 for c in grouped.values())

def test_missing_p_group_fails():
    c=fixture_counts()
    del c[("YEAR_QUARANTINE_P",COHORT+"|2016|P=0|NONE")]
    with pytest.raises(ValueError):
        s85.summarize(c,COHORT,FakeStep70)

def test_empty_p_group_fails_even_if_n_positive_elsewhere():
    c=fixture_counts()
    c[("YEAR_QUARANTINE_P",COHORT+"|2016|P=0|NONE")]["n"]=0
    with pytest.raises(ValueError):
        s85.summarize(c,COHORT,FakeStep70)

def test_nonbinomial_counts_fail():
    c=fixture_counts()
    c[("YEAR_QUARANTINE_P",COHORT+"|2016|P=0|NONE")]["inpatient"]=1000000
    with pytest.raises(ValueError,match="Non-binomial"):
        s85.summarize(c,COHORT,FakeStep70)

def test_restricted_output_rejects_repository_root(tmp_path):
    with pytest.raises(ValueError,match="gitignored"):
        s85.save_private(tmp_path/"unsafe.json",{"synthetic":True})
