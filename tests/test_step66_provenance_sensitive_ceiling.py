"""Step66 synthetic-only ED-link flags and ceiling semantics."""
import sqlite3
import pytest
from scripts import step66_provenance_sensitive_ceiling as s


@pytest.fixture
def data():
    db=sqlite3.connect(":memory:")
    db.executescript("""
    CREATE TABLE idx(cohort TEXT,patient TEXT,encounter TEXT,start TEXT,
      end TEXT,principal INTEGER, PRIMARY KEY(cohort,patient));
    CREATE TABLE evt(patient TEXT,encounter TEXT,kind TEXT,start TEXT,end TEXT,
      derived TEXT,start_derived TEXT,end_derived TEXT,
      PRIMARY KEY(patient,encounter));
    CREATE TABLE linked(cohort TEXT,patient TEXT,ed TEXT,imp TEXT,
      ed_start TEXT,ed_end TEXT,PRIMARY KEY(cohort,patient));
    ATTACH DATABASE ':memory:' AS baseline;
    CREATE TABLE baseline.idx(cohort TEXT,patient TEXT,encounter TEXT,start TEXT,
      end TEXT,principal INTEGER,PRIMARY KEY(cohort,patient));
    CREATE TABLE baseline.image(cohort TEXT,patient TEXT,category TEXT,
      PRIMARY KEY(cohort,patient,category));
    """)
    uni="uniform_18_50"
    hist="historical_sex_specific_18_52_54"
    patients=[
        ("PATA","20200103",1,"2020-01-03","2020-01-03","F","F","F"),
        ("PATB","20200103",1,"2020-01-02","2020-01-03","T","F","T"),
        ("PATC","20200103",0,"2020-01-02","2020-01-03","T","F","F"),
        ("PATD","20200103",0,"2020-01-03","2020-01-03","F","F","F"),
        ("PATE","20210103",1,"2021-01-02","2021-01-03","F","F","F"),
        ("PATF","20210103",0,"2021-01-02","2021-01-03","F","F","F"),
    ]
    for person, day, principal,ed_end,imp_start,derived,start_flag,end_flag in patients:
        encounter="IP_"+person
        db.execute("INSERT INTO baseline.idx VALUES(?,?,?,?,?,?)",
                   (uni,person,encounter,day,day,principal))
        db.execute("INSERT INTO idx VALUES(?,?,?,?,?,?)",
                   (uni,person,encounter,day,day,principal))
        db.execute("INSERT INTO evt VALUES(?,?,?,?,?,?,?,?)",
                   (person,encounter,"IMP",imp_start,imp_start,"F","F","F"))
        db.execute("INSERT INTO evt VALUES(?,?,?,?,?,?,?,?)",
                   (person,"ED_"+person,"EMER",ed_end,ed_end,
                    derived,start_flag,end_flag))
        db.execute("INSERT INTO linked VALUES(?,?,?,?,?,?)",
                   (uni,person,"ED_"+person,encounter,ed_end,ed_end))
    db.execute("INSERT INTO baseline.image VALUES(?,?,?)",
               (uni,"PATA","CT_HEAD"))
    db.execute("INSERT INTO baseline.image VALUES(?,?,?)",
               (uni,"PATF","MRI_BRAIN"))
    for name in ("PATG","PATH"):
        db.execute("INSERT INTO baseline.idx VALUES(?,?,?,?,?,?)",
                   (uni,name,"IP_"+name,"20210103","20210104",0))
        db.execute("INSERT INTO idx VALUES(?,?,?,?,?,?)",
                   (uni,name,"IP_"+name,"20210103","20210104",0))
    db.execute("INSERT INTO baseline.idx VALUES(?,?,?,?,?,?)",
               (hist,"PATJ","IP_PATJ","20200103","20200104",1))
    db.execute("INSERT INTO idx VALUES(?,?,?,?,?,?)",
               (hist,"PATJ","IP_PATJ","20200103","20200104",1))
    db.execute("INSERT INTO evt VALUES(?,?,?,?,?,?,?,?)",
               ("PATJ","IP_PATJ","IMP","2020-01-03","2020-01-04",
                "F","F","F"))
    db.execute("INSERT INTO evt VALUES(?,?,?,?,?,?,?,?)",
               ("PATJ","ED_PATJ","EMER","2020-01-02","2020-01-02",
                "F","F","F"))
    db.execute("INSERT INTO linked VALUES(?,?,?,?,?,?)",
               (hist,"PATJ","ED_PATJ","IP_PATJ","2020-01-02","2020-01-02"))
    db.commit()
    yield db
    db.close()


def test_derived_end_reduces_bound_and_partition(data):
    rows=s.analyze(data)
    u=dict(s.grouped(rows,"cohort"))[("uniform_18_50",)]
    assert u["indexed"]==8
    assert u["inpatient_any"]==2
    assert (u["links_all"],u["new_all"])==(6,4)
    assert (u["links_critical"],u["new_critical"])==(5,3)
    assert (u["links_all_ed"],u["new_all_ed"])==(4,2)
    assert (u["links_same"],u["new_same"])==(2,1)
    assert (u["links_next"],u["new_next"])==(3,2)
    assert u["invalid_gap"]==0
    h=dict(s.grouped(rows,"cohort"))[
        ("historical_sex_specific_18_52_54",)]
    assert (h["indexed"],h["new_all"],h["new_critical"])==(1,1,1)


def test_year_and_P_labels_preserved(data):
    rows=s.analyze(data)
    p=dict(s.grouped(rows,"P"))
    p1=p[("uniform_18_50",1)]
    assert p1["indexed"]==3
    assert p1["new_all"]==2
    assert p1["new_critical"]==1
    years=dict(s.grouped(rows,"year"))
    assert years[("uniform_18_50","2020")]["new_all"]==3
    assert years[("uniform_18_50","2021")]["new_all"]==1
    with pytest.raises(ValueError,match="Unsupported"):
        s.grouped(rows,"unsupported")


def test_invalid_ED_window_rejected(data):
    data.execute("UPDATE evt SET end='2020-01-01' "
                 "WHERE patient='PATD' AND encounter='ED_PATD'")
    with pytest.raises(ValueError,match="outside frozen"):
        s.analyze(data)


def test_orphaned_ED_event_rejected(data):
    data.execute("DELETE FROM evt WHERE patient='PATB' AND encounter='ED_PATB'")
    with pytest.raises(ValueError,match="linked ED event missing"):
        s.analyze(data)


def test_prints_no_identifiers(data,capsys):
    s.show(s.analyze(data))
    out=capsys.readouterr().out
    assert "provenance-sensitive" in out
    assert "max_new" in out
    assert "suppressed:" in out
    for val in ("PATA","PATB","IP_PATA","ED_PATB"):
        assert val not in out
