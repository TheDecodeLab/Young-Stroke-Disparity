"""Step69 fabricated-only source-quality tests. No patient data."""
from collections import Counter
import sqlite3

import pytest

from scripts import step68_joint_imaging_window_scan as s68
from scripts import step69_same_day_attachment_diagnostics as s69
from scripts import step62_checkpointed_cohort as s62


@pytest.fixture
def fake():
    db=sqlite3.connect(":memory:")
    db.executescript("""
    CREATE TABLE idx(cohort TEXT,patient TEXT,encounter TEXT,start TEXT,
                     end TEXT,principal INTEGER,PRIMARY KEY(cohort,patient));
    CREATE TABLE linked(cohort TEXT,patient TEXT,ed TEXT,imp TEXT,
                        ed_start TEXT,ed_end TEXT,PRIMARY KEY(cohort,patient));
    CREATE TABLE ambiguous(patient TEXT,encounter TEXT,PRIMARY KEY(patient,encounter));
    ATTACH DATABASE ':memory:' AS baseline;
    CREATE TABLE baseline.idx(cohort TEXT,patient TEXT,encounter TEXT,start TEXT,
                     end TEXT,principal INTEGER,PRIMARY KEY(cohort,patient));
    CREATE TABLE baseline.image(cohort TEXT,patient TEXT,category TEXT,
                     PRIMARY KEY(cohort,patient,category));
    ATTACH DATABASE ':memory:' AS capture;
    CREATE TABLE capture.progress(stage TEXT PRIMARY KEY,seen INTEGER,done INTEGER);
    CREATE TABLE capture.flags(cohort TEXT,patient TEXT,modality TEXT,mask INTEGER,
                     PRIMARY KEY(cohort,patient,modality));
    CREATE TABLE capture.code_profile(system TEXT,code TEXT,scope TEXT,
                      service_year TEXT,P INTEGER,n INTEGER,
                      PRIMARY KEY(system,code,scope,service_year,P));
    """)
    mask={
        "A1":s68.IMP|s68.ANY_DAY0,
        "A2":s68.NONIMP_DAY0|s68.ANY_DAY0,
        "A3":s68.ED|s68.ED_F|s68.NONIMP_DAY0|s68.NONIMP_PRE2|s68.NONIMP_PRE7,
        "A4":s68.NONIMP_DAY0|s68.NONIMP_PRE2|s68.NONIMP_POST2|s68.NONIMP_PRE7,
        "B1":s68.ED|s68.NONIMP_PRE2|s68.NONIMP_PRE7,
        "B2":s68.IMP|s68.NONIMP_DAY0,
    }
    for cohort in s62.COHORTS:
        for p,m in mask.items():
            is_primary=int(p.startswith("A"))
            indexed=(cohort,p,p+"IP","20200105","20200106",is_primary)
            db.execute("INSERT INTO idx VALUES(?,?,?,?,?,?)",indexed)
            db.execute("INSERT INTO baseline.idx VALUES(?,?,?,?,?,?)",indexed)
            db.execute("INSERT INTO capture.flags VALUES(?,?,?,?)",
                       (cohort,p,"CT_HEAD",m))
            if p in ("A1","B2"):
                db.execute("INSERT INTO baseline.image VALUES(?,?,?)",
                           (cohort,p,"CT_HEAD"))
            if p in ("A3","B1"):
                db.execute("INSERT INTO linked VALUES(?,?,?,?,?,?)",
                           (cohort,p,p+"ED",p+"IP","2020-01-04","2020-01-04"))
    db.execute("INSERT INTO ambiguous VALUES('A2','A2OTHER')")
    db.execute("INSERT INTO capture.progress VALUES('procedure',993025015,1)")
    db.executemany("INSERT INTO capture.code_profile VALUES(?,?,?,?,?,?)",[
        ("ICD-10-PCS","B030ZZZ","INDEX_IMP","2020",1,14),
        ("ICD-10-PCS","B040ZZZ","INDEX_IMP","2020",0,8),
        ("ICD-10-PCS","B050ZZZ","NONIMP_DAY0","2020",1,32),
        ("ICD-10-PCS","AB12345","NONIMP_DAY0","2020",1,15),
        ("ICD-10-PCS","TOO_LONG_CODE","INDEX_IMP","2020",0,11),
    ])
    db.commit()
    yield db
    db.close()


def test_day0_unlinked_vs_ED_linked_P(fake):
    c=s69.aggregate(fake)
    for cohort in s62.COHORTS:
        p1=c[("P",cohort+"|P=1")]
        p0=c[("P",cohort+"|P=0")]
        assert p1["n"]==4 and p1["inpatient"]==1
        assert p1["new_other_day0"]==3
        assert p1["new_other_day0_unlinked"]==2
        assert p1["new_other_day0_not_ED"]==2
        assert p1["new_ed"]==1 and p1["ed_new_and_day0"]==1
        assert p0["n"]==2 and p0["inpatient"]==1
        assert p0["new_other_day0"]==0 and p0["new_ed"]==1
        linked_p1=c[("EDLINK_P",cohort+"|P=1|UNIQUE_ED")]
        unlinked_p1=c[("EDLINK_P",cohort+"|P=1|NO_UNIQUE_ED")]
        assert linked_p1["new_other_day0"]==1
        assert unlinked_p1["new_other_day0"]==2
        quarantined=c[("QUARANTINE_P",cohort+"|P=1|ANY_AMBIG")]
        assert quarantined["n"]==1 and quarantined["new_other_day0"]==1


def test_original_baseline_and_windows_reconcile(fake):
    c=s69.aggregate(fake)
    assert s69.verify_aggregate(fake,c)
    for cohort in s62.COHORTS:
        a=c[("COHORT",cohort)]
        assert a["n"]==6
        assert a["inpatient"]==2
        assert a["new_other_day0"]==3
        assert a["new_ed"]==2
        assert a["new_ed_f"]==1
        assert a["union_ed_or_day0"]==4
        assert a["union_ed_or_pre2_day0"]==4
        assert a["union_ed_or_pre7_day0"]==4
        assert a["union_ed_or_pre2_day0_post2"]==4
        published={"patient_cohort_aggregates":{
            "COHORT|"+cohort:{
                "n":a["n"],"imp":a["inpatient"],"new_ed":a["new_ed"],
                "new_ed_f":a["new_ed_f"],
                "new_day0_other":a["new_other_day0"],
                "new_pre2":a["new_pre2"],
                "new_post2_other":a["new_post2"],
                "new_pre7":a["new_pre7"],
                "new_ed_or_pre2_day0":a["union_ed_or_pre2_day0"],
                "new_ed_or_pre7_day0":a["union_ed_or_pre7_day0"],
                "new_ed_or_pre2_day0_post2":
                    a["union_ed_or_pre2_day0_post2"]}}}
        assert s69.verify_aggregate(fake,c,published) is True
    changed={"patient_cohort_aggregates":{
        "COHORT|"+cohort:{
            "imp":99999} for cohort in s62.COHORTS}}
    with pytest.raises(ValueError,match="discrepancy"):
        s69.verify_aggregate(fake,c,changed)


def test_rejects_inconsistent_mask(fake):
    fake.execute("""UPDATE capture.flags SET mask=?
                  WHERE cohort=? AND patient='A2'""",
                 (s68.ED,s62.COHORTS[0]))
    with pytest.raises(ValueError,match="no frozen"):
        s69.aggregate(fake)


def test_prefix_discovery_is_not_patient_outcome(fake,capsys):
    s69.code_family_discovery(fake)
    output=capsys.readouterr().out
    assert "B_prefix_rows_unreviewed 14" in output
    assert "B_prefix_rows_unreviewed 32" in output
    assert "B03:14" in output
    assert "B05:32" in output
    assert "TOO_LONG_CODE" not in output


def test_small_group_suppression_and_big_group_print(fake,capsys):
    s69.display(s69.aggregate(fake))
    txt=capsys.readouterr().out
    assert "Suppressed group n<11" in txt
    for p in ("A1","A2","B1","B2"):
        assert p not in txt
    counts={("P","synthetic|P=1"):Counter(
        n=15,inpatient=4,new_other_day0=8,
        new_other_day0_unlinked=5,new_other_day0_not_ED=6,
        new_ed=2,ed_new_and_day0=1,
        new_pre2=3,new_post2=2,
        union_ed_or_pre2_day0=10,
        union_ed_or_pre7_day0=11,
        union_ed_or_pre2_day0_post2=12),
        ("P","synthetic|P=0"):Counter(
        n=15,inpatient=7,new_other_day0=3)}
    # Contrast needs a cohort for every result, so add complete cohorts.
    for cohort in s62.COHORTS:
        counts[("P",cohort+"|P=0")]=Counter(n=15,inpatient=7)
        counts[("P",cohort+"|P=1")]=Counter(n=15,inpatient=4)
    s69.display(counts)
    assert "IMP_or_DAY0_pct" in capsys.readouterr().out
