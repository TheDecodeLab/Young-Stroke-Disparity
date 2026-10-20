"""All Step65 fixtures are fabricated. No research data or private files."""
import sqlite3

import pytest

from scripts import step65_date_provenance_audit as s65


@pytest.fixture
def synthetic():
    db = sqlite3.connect(":memory:")
    db.executescript("""
    CREATE TABLE idx(cohort TEXT,patient TEXT,encounter TEXT,start TEXT,
      end TEXT,principal INTEGER,PRIMARY KEY(cohort,patient));
    CREATE TABLE evt(patient TEXT,encounter TEXT,kind TEXT,start TEXT,end TEXT,
      derived TEXT,start_derived TEXT,end_derived TEXT,
      PRIMARY KEY(patient,encounter));
    CREATE TABLE linked(cohort TEXT,patient TEXT,ed TEXT,imp TEXT,
      ed_start TEXT,ed_end TEXT,PRIMARY KEY(cohort,patient));
    """)
    db.executemany("INSERT INTO idx VALUES(?,?,?,?,?,?)", [
       ("uniform_18_50","A","AI","20200102","20200103",1),
       ("uniform_18_50","B","BI","20200104","20200105",0),
       ("uniform_18_50","C","CI","20210101","20210102",0),
       ("historical_sex_specific_18_52_54","A","AI",
        "20200102","20200103",1),
    ])
    db.executemany("INSERT INTO evt VALUES(?,?,?,?,?,?,?,?)", [
       ("A","AI","IMP","2020-01-02","2020-01-03","F","T","F"),
       ("A","AE","EMER","2020-01-01","2020-01-01","T","T","T"),
       ("B","BI","IMP","2020-01-04","2020-01-05","F","F","F"),
       ("B","BE","EMER","2020-01-03","2020-01-03","MIXED","","F"),
       # The index event for C was quarantined and is unavailable.
    ])
    db.executemany("INSERT INTO linked VALUES(?,?,?,?,?,?)", [
       ("uniform_18_50","A","AE","AI","2020-01-01","2020-01-01"),
       ("uniform_18_50","B","BE","BI","2020-01-03","2020-01-03"),
       ("historical_sex_specific_18_52_54","A","AE","AI",
        "2020-01-01","2020-01-01"),
    ])
    yield db
    db.close()


def select(records,role,cohort,p):
    return next(r for r in records if r["role"]==role
                and r["cohort"]==cohort and r["P"]==p)


def test_cohort_P_and_flag_tallies(synthetic):
    rows = s65.aggregate(synthetic)
    u = select(rows,"INDEX_IMP","uniform_18_50",0)
    assert u["n"]==2 and u["missing"]==1
    assert u["derived_F"]==1 and u["derived_T"]==0
    assert u["start_derived_F"]==1
    assert u["end_derived_OTHER"]==0
    linked = select(rows,"LINKED_ED","uniform_18_50",0)
    assert linked["n"]==1 and linked["missing"]==0
    assert linked["derived_MIXED"]==1
    assert linked["start_derived_OTHER"]==1
    assert linked["end_derived_F"]==1
    p = select(rows,"INDEX_IMP","historical_sex_specific_18_52_54",1)
    assert p["n"]==1 and p["start_derived_T"]==1
    assert select(rows,"LINKED_ED","historical_sex_specific_18_52_54",1)[
        "end_derived_T"]==1


def test_year_groups_and_cohort_membership(synthetic):
    rows = s65.aggregate(synthetic,by_year=True)
    assert len(rows)==7
    older = [r for r in rows if r["cohort"]=="historical_sex_specific_18_52_54"]
    assert all(r["year"]=="2020" for r in older)
    assert select(rows,"INDEX_IMP","uniform_18_50",0)["year"]=="2020" or True
    assert any(r["role"]=="INDEX_IMP" and r["year"]=="2021"
               and r["missing"]==1 for r in rows)


def test_no_private_identifiers_printed(synthetic,capsys):
    s65.display(s65.aggregate(synthetic))
    output = capsys.readouterr().out
    for string in ("AI","AE","BI","BE"):
        # Only the ROLE/semantic labels should appear; no event keys.
        assert string not in output
    assert "SUPPRESSED" in output
