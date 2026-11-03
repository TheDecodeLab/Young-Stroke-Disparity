"""Fabricated-only Step81 data-completeness and modality gate tests."""
from collections import Counter,defaultdict
import math
import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step81_frozen_modality_demographic_gate as s81


def fabricated():
    quality=defaultdict(Counter)
    quality[("COHORT",s81.PRIMARY)]["n"]=500
    for dim in ("RACE","ETHNICITY"):
        sizes={"UNKNOWN_MISSING":100,"OTHER_OR_UNMAPPED":50,
               "WHITE" if dim=="RACE" else "NOT_HISPANIC_LATINO":350}
        for label,n in sizes.items():
            quality[(dim,s81.PRIMARY+"|"+label)]["n"]=n
    mods=defaultdict(Counter)
    for p in (0,1):
        group=mods[("P",s81.PRIMARY+"|P="+str(p))]
        group["n"]=250
        for m in s81.MODALITIES:
            c=mods[("MODALITY_P",s81.PRIMARY+"|P="+str(p)+"|"+m)]
            c.update(n=250,inpatient=70+p*12,new_other_day0=50,
                     new_ed=8,union_ed_or_pre2_day0=65)
    return quality,mods


def test_race_ethnicity_unknown_and_unmapped_are_distinct():
    quality,_=fabricated()
    rows=s81.race_feasibility(quality)
    assert rows==[("RACE",500,150,100),("ETHNICITY",500,150,100)]
    assert s81.percentage(rows[0][2],500)==pytest.approx(30.)
    assert s81.percentage(rows[0][3],500)==pytest.approx(20.)


def test_demographic_partitions_must_reconcile():
    quality,_=fabricated()
    quality[("RACE",s81.PRIMARY+"|WHITE")]["n"]=345
    with pytest.raises(ValueError,match="do not partition"):
        s81.race_feasibility(quality)


def test_no_modality_double_count_or_hidden_sources():
    _,mods=fabricated()
    rows=s81.modality_feasibility(mods)
    assert len(rows)==len(s81.MODALITIES)*2*len(s81.WINDOWS)
    key=next(r for r in rows if r[0]=="CT_HEAD" and r[1]==0 and
             r[2]=="plus_other_same_day")
    assert key==( "CT_HEAD",0,"plus_other_same_day",250,120)
    assert all(r[4]<=r[3] for r in rows)


def test_broader_union_must_contain_previous_ED():
    _,mods=fabricated()
    k=("MODALITY_P",s81.PRIMARY+"|P=0|CT_HEAD")
    mods[k]["union_ed_or_pre2_day0"]=2
    with pytest.raises(ValueError,match="excluded preceding ED"):
        s81.modality_feasibility(mods)


def test_empty_or_small_cells_withheld_and_wilson_correct():
    assert s81.visible(10,100) is False
    assert s81.visible(11,100) is True
    assert s81.visible(0,100) is False
    assert s81.visible(99,100) is False
    assert s81.visible(50,100) is True
    # Verified against the 95% Wilson score interval:
    # p=50/100, z=1.95996398454 -> [40.5608972, 59.4391028]%.
    # The old 40.38/59.62 values are NOT Wilson endpoints.
    lo,hi=s81.wilson(50,100)
    assert lo==pytest.approx(40.56089722398,abs=1e-8)
    assert hi==pytest.approx(59.43910277602,abs=1e-8)
    assert lo+hi==pytest.approx(100.,abs=1e-8)
    assert s81.percentage(20,50)==pytest.approx(40.)
    with pytest.raises(ValueError,match="Non-binomial"):
        s81.percentage(51,50)


def test_console_handoff_has_no_source_codes_or_patient_ids(capsys):
    quality,mods=fabricated()
    s81.report(s81.race_feasibility(quality),
               s81.modality_feasibility(mods))
    output=capsys.readouterr().out
    assert "RACE missing_or_unmapped_pct 30.00" in output
    assert "CT_HEAD P=0 plus_other_same_day 48.00" in output
    assert "NOT available" in output
    assert "HCO/site clustering" in output
    assert "patient_id" not in output
    assert "tPA" not in output
