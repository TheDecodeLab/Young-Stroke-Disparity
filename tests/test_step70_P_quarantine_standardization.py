"""Synthetic-only tests for descriptive, noncausal standardization."""
from collections import Counter, defaultdict
import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step70_P_quarantine_standardization as s70


@pytest.fixture
def fake():
    out=defaultdict(Counter)
    # Contrived strong P mix imbalance: P0 mostly clean, P1 mostly ambiguous.
    # Each YEAR x AMBIG x P cell has support. Both cohorts are independent
    # synthetic duplicates to test cohort separation, NOT extra patients.
    samples=[
        ("2020","NONE",0,20,10,2),
        ("2020","NONE",1,10,3,3),
        ("2020","ANY_AMBIG",0,10,2,6),
        ("2020","ANY_AMBIG",1,20,1,16),
        ("2021","NONE",0,20,10,2),
        ("2021","NONE",1,10,4,2),
        ("2021","ANY_AMBIG",0,10,3,5),
        ("2021","ANY_AMBIG",1,20,2,14),
    ]
    for cohort in s62.COHORTS:
        for yr,held,p,n,imp,day in samples:
            row=Counter(n=n,inpatient=imp,new_other_day0=day,
                        new_ed=min(2,day),union_ed_or_pre2_day0=day)
            keys=(
                ("COHORT",cohort),
                ("P",cohort+"|P="+str(p)),
                ("YEAR_P",cohort+"|"+yr+"|P="+str(p)),
                ("QUARANTINE_P",cohort+"|P="+str(p)+"|"+held),
                ("YEAR_QUARANTINE_P",
                 cohort+"|"+yr+"|P="+str(p)+"|"+held),
            )
            for key in keys:
                out[key].update(row)
    return out


def test_crude_vs_common_quarantine_and_year_weights(fake):
    for cohort in s62.COHORTS:
        f=("inpatient","new_other_day0")
        crude=s70.raw(fake,cohort,f)
        joint=s70.standardized(fake,cohort,f,"year_and_quarantine")
        quarantine=s70.standardized(fake,cohort,f,"quarantine")
        year=s70.standardized(fake,cohort,f,"year")
        assert crude[0]==pytest.approx(100*40/60)
        assert crude[1]==pytest.approx(100*45/60)
        assert crude[2]==pytest.approx(100*5/60)
        assert joint[0]==pytest.approx(70.0)
        assert joint[1]==pytest.approx(71.25)
        assert joint[2]==pytest.approx(1.25)
        assert quarantine[2]==pytest.approx(1.25)
        assert year[2]==pytest.approx(crude[2])
        assert s70.raw(fake,cohort,("inpatient",),"NONE")[0]==50.0


def test_year_strata_partition_and_support(fake):
    cohort=s62.COHORTS[0]
    cells=s70.strata(fake,cohort,"year_and_quarantine")
    assert len(cells)==4
    assert set(cells)=={
        ("2020","NONE"),("2020","ANY_AMBIG"),
        ("2021","NONE"),("2021","ANY_AMBIG")}
    assert sum(cell[p]["n"] for cell in cells.values()
               for p in (0,1))==120
    with pytest.raises(ValueError,match="Unsupported|No source-quality"):
        s70.strata(fake,cohort,"bad")  # rejects unknown name
    del fake[("YEAR_QUARANTINE_P",cohort+"|2021|P=1|ANY_AMBIG")]
    with pytest.raises(ValueError,match="Cannot standardize"):
        s70.standardized(fake,cohort,("inpatient",),"year_and_quarantine")


def test_rejects_inconsistent_stratum_sample_size(fake):
    cohort=s62.COHORTS[0]
    row=fake[("YEAR_QUARANTINE_P",cohort+"|2020|P=0|NONE")]
    row["n"]+=1
    with pytest.raises(ValueError,match="full cohort coverage"):
        s70.standardized(fake,cohort,("inpatient",),"year_and_quarantine")


def test_local_printing_uses_only_aggregates(fake,capsys):
    s70.display(fake)
    output=capsys.readouterr().out
    assert "standardized_same_year_and_quarantine_mix" in output
    assert "P1_minus_P0_pp" in output
    assert "YEAR × QUARANTINE" in output
    assert "P=0" in output
    assert "adjudicated" not in output.lower()


def test_raw_group_has_disjoint_denominator(fake):
    cohort=s62.COHORTS[0]
    p0=fake[("P",cohort+"|P=0")]
    p1=fake[("P",cohort+"|P=1")]
    assert p0["n"]+p1["n"]==fake[("COHORT",cohort)]["n"]
    assert (fake[("QUARANTINE_P",cohort+"|P=0|NONE")]["n"]+
            fake[("QUARANTINE_P",cohort+"|P=0|ANY_AMBIG")]["n"])==p0["n"]
