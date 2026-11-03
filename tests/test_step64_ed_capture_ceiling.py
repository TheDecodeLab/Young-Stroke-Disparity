"""Synthetic-only audit of ceiling calculations, never clinical records."""
import sqlite3

import pytest

from scripts import step64_ed_capture_ceiling as ceiling


@pytest.fixture
def fixture_db():
    db = sqlite3.connect(":memory:")
    db.executescript("""
    CREATE TABLE linked(cohort TEXT,patient TEXT,ed TEXT,imp TEXT,
      ed_start TEXT,ed_end TEXT,PRIMARY KEY(cohort,patient));
    ATTACH DATABASE ':memory:' AS baseline;
    CREATE TABLE baseline.idx(
      cohort TEXT,patient TEXT,encounter TEXT,start TEXT,end TEXT,
      principal INTEGER,PRIMARY KEY(cohort,patient));
    CREATE TABLE baseline.image(cohort TEXT,patient TEXT,category TEXT,
      PRIMARY KEY(cohort,patient,category));
    """)
    # Note: A has two modality codes but remains one baseline patient.
    records = [
        ("uniform_18_50","A","AIP","20200103","20200105",1),
        ("uniform_18_50","B","BIP","20200103","20200105",1),
        ("uniform_18_50","C","CIP","20210103","20210105",0),
        ("uniform_18_50","D","DIP","20210103","20210105",0),
        ("historical_sex_specific_18_52_54","E","EIP","20200103","20200105",0),
        ("historical_sex_specific_18_52_54","F","FIP","20200103","20200105",1),
        ("historical_sex_specific_18_52_54","G","GIP","20210103","20210105",1),
    ]
    db.executemany("INSERT INTO baseline.idx VALUES(?,?,?,?,?,?)", records)
    db.executemany("INSERT INTO baseline.image VALUES(?,?,?)", [
        ("uniform_18_50","A","CT_HEAD"),
        ("uniform_18_50","A","MRI_BRAIN"),
        ("uniform_18_50","C","CT_HEAD"),
        ("historical_sex_specific_18_52_54","F","MRI_BRAIN"),
    ])
    db.executemany("INSERT INTO linked VALUES(?,?,?,?,?,?)", [
        ("uniform_18_50","A","AED","AIP","20200102","20200102"),
        ("uniform_18_50","B","BED","BIP","20200102","20200102"),
        ("historical_sex_specific_18_52_54","E","EED","EIP",
         "20200102","20200102"),
        ("historical_sex_specific_18_52_54","F","FED","FIP",
         "20200102","20200102"),
    ])
    yield db
    db.close()


def test_any14_ceiling_counts_unique_patients_and_existing_overlap(fixture_db):
    rows = ceiling.analyze(fixture_db)
    by_cohort = dict(ceiling.summarize(rows, "cohort"))
    u = by_cohort[("uniform_18_50",)]
    h = by_cohort[("historical_sex_specific_18_52_54",)]
    assert (u["n"], u["linked"], u["baseline_any14"],
            u["max_new_any14"]) == (4,2,2,1)
    assert (h["n"], h["linked"], h["baseline_any14"],
            h["max_new_any14"]) == (3,2,1,1)
    assert u["baseline_CT_HEAD"] == 2
    assert u["baseline_MRI_BRAIN"] == 1
    assert u["max_new_CT_HEAD"] == 1
    # A has inpatient CT and MRI; B's linked ED could hypothetically add both.
    assert u["max_new_MRI_BRAIN"] == 1
    # F's existing inpatient MRI means F is not counted as a new MRI patient.
    assert h["max_new_MRI_BRAIN"] == 1
    assert ceiling.pct(u["max_new_any14"],u["n"]) == 25.0


def test_grouping_keeps_overlapping_cohorts_and_P_separate(fixture_db):
    rows = ceiling.analyze(fixture_db)
    p = dict(ceiling.summarize(rows, "P"))
    assert p[("uniform_18_50",1)]["n"] == 2
    assert p[("uniform_18_50",1)]["max_new_any14"] == 1
    assert p[("uniform_18_50",0)]["max_new_any14"] == 0
    assert p[("historical_sex_specific_18_52_54",0)]["max_new_any14"] == 1
    y = dict(ceiling.summarize(rows, "year"))
    assert y[("uniform_18_50","2020")]["n"] == 2
    assert y[("uniform_18_50","2021")]["n"] == 2
    assert sum(count["n"] for _,count in ceiling.summarize(rows,"cohort")) == 7


def test_raises_on_invalid_group(fixture_db):
    rows = ceiling.analyze(fixture_db)
    with pytest.raises(ValueError,match="Unknown group"):
        ceiling.summarize(rows, "not_a_group")


def test_prints_aggregate_only_no_private_keys(fixture_db, capsys):
    ceiling.show(ceiling.analyze(fixture_db))
    rendered = capsys.readouterr().out
    assert "UPPER BOUNDS" in rendered
    assert "ED procedure rows" in rendered
    # The identifiers are synthetic-only and must not leak into display.
    for identifier in ("AIP", "AED", "FED", "GIP"):
        assert identifier not in rendered
    assert "GROUP SUPPRESSED" in rendered
