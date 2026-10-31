"""Step76 fully fabricated CMS and private-row fixtures; no clinical records."""
from collections import Counter
import json
import sqlite3

import pytest

from scripts import step76_exact_PCS_anatomy_review as s76


@pytest.fixture
def titles():
    brain="Computerized Tomography of Brain"
    mr="Magnetic Resonance Imaging of Brain"
    vessel="Computerized Tomography of Bilateral Internal Carotid Arteries"
    artery="Magnetic Resonance Imaging of Intracranial Arteries"
    unrelated="Magnetic Resonance Imaging of Thoracic Aorta"
    cached={}
    for yr in range(2016,2026):
        cached[yr]={
            "B020ZZZ":brain,"B030ZZZ":mr,
            "B328ZZZ":vessel,"B33RZZZ":artery,
            "B330ZZZ":unrelated,
        }
    return cached


@pytest.fixture
def fake_step74():
    records=[
        (2017,0,"INDEX_IMP","B020ZZZ",16),
        (2017,0,"INDEX_IMP","B328ZZZ",35),
        (2017,1,"INDEX_IMP","B030ZZZ",22),
        (2021,0,"NONIMP_DAY0","B33RZZZ",14),
        # A non-stroke artery was permitted through the earlier broad
        # code-title logic? Here it is deliberately included in the
        # fabricated review queue to ensure Step76 does not approve it.
        (2021,1,"INDEX_IMP","B330ZZZ",19),
    ]
    mapping={
        "B020ZZZ":"Computerized Tomography of Brain",
        "B030ZZZ":"Magnetic Resonance Imaging of Brain",
        "B328ZZZ":"Computerized Tomography of Bilateral Internal Carotid Arteries",
        "B33RZZZ":"Magnetic Resonance Imaging of Intracranial Arteries",
        "B330ZZZ":"Magnetic Resonance Imaging of Thoracic Aorta",
    }
    tags={"B020ZZZ":"REVIEW_CNS_CT","B030ZZZ":"REVIEW_CNS_MR",
          "B328ZZZ":"REVIEW_UPPER_ARTERIAL_CT",
          "B33RZZZ":"REVIEW_UPPER_ARTERIAL_MR",
          "B330ZZZ":"REVIEW_UPPER_ARTERIAL_MR"}
    detail=[]
    aggregates={}
    for year,P,scope,code,n in records:
        row={"service_year":str(year),"P":P,"scope":scope,"code":code,
             "source_rows_cohort_memberships":n,
             "FY_codes_available":[year,year+1],
             "FY_titles":[mapping[code],mapping[code]],
             "review_tags":[tags[code]]}
        detail.append(row)
        label="|".join(map(str,(year,P,scope)))
        c=aggregates.setdefault(label,{
            "source_rows":0,
            "REVIEW_ONLY_potential_neuroimaging_source_rows":0})
        c["source_rows"]+=n
        c["REVIEW_ONLY_potential_neuroimaging_source_rows"]+=n
    return {"policy":"STEP74_DISCOVERY_ONLY_V1",
            "public_codes_plus_private_source_frequencies_LOCAL_ONLY":detail,
            "source_row_aggregates_LOCAL_ONLY":aggregates}


def test_anatomy_review_is_not_automatic_approval(titles):
    assert s76.judgment("B020ZZZ",[titles[2017]["B020ZZZ"]]) == (
        "BRAIN_ANATOMY_CANDIDATE")
    assert s76.judgment("B328ZZZ",[titles[2017]["B328ZZZ"]]) == (
        "HEAD_NECK_VESSEL_CANDIDATE")
    assert s76.judgment("B330ZZZ",[titles[2017]["B330ZZZ"]]) == (
        "ANATOMY_UNRESOLVED")
    with pytest.raises(ValueError,match="Candidate"):
        s76.judgment("B24",["Ultrasonography of Heart"])


def test_crosswalk_candidate_coverage_reconciles(fake_step74,titles):
    counts,queue=s76.assess(fake_step74,titles)
    assert len(queue)==5
    assert sum(q["observed_source_rows_cohort_memberships"]
               for q in queue)==106
    assert counts[("MODE","CNS_CT")]["candidate_rows"]==16
    assert counts[("MODE","UPPER_ARTERY_CT")]["candidate_rows"]==35
    assert counts[("SCOPE","NONIMP_DAY0")]["candidate_rows"]==14
    assert counts[("YEAR","2017")]["candidate_rows"]==73
    assert counts[("YEAR","2021")]["candidate_rows"]==33
    assert sum(q["anatomy_review_status"]=="ANATOMY_UNRESOLVED"
               for q in queue)==1
    assert all(q["clinical_reviewer_approval"]=="PENDING" for q in queue)
    assert all(q["exact_discharge_date_validity"]=="NOT_ASSESSED" for q in queue)
    assert all("patient_id" not in q for q in queue)


def test_rejects_conflicts_and_modified_evidence(fake_step74,titles):
    bad=json.loads(json.dumps(fake_step74))
    bad["public_codes_plus_private_source_frequencies_LOCAL_ONLY"][0][
        "FY_titles"]=["Different title","Different title"]
    with pytest.raises(ValueError,match="official CMS title changed"):
        s76.assess(bad,titles)
    other=json.loads(json.dumps(fake_step74))
    other["public_codes_plus_private_source_frequencies_LOCAL_ONLY"].append(
        dict(other["public_codes_plus_private_source_frequencies_LOCAL_ONLY"][0]))
    with pytest.raises(ValueError,match="Duplicate Step74"):
        s76.assess(other,titles)
    third=json.loads(json.dumps(fake_step74))
    first=next(iter(third["source_row_aggregates_LOCAL_ONLY"].values()))
    first["REVIEW_ONLY_potential_neuroimaging_source_rows"]+=1
    with pytest.raises(ValueError,match="differ from Step74"):
        s76.assess(third,titles)


def test_read_only_B_denominator_reconciliation(tmp_path,fake_step74):
    db=tmp_path/"synthetic_only.db"
    con=sqlite3.connect(str(db))
    con.execute("""CREATE TABLE code_profile(system TEXT,code TEXT,
        scope TEXT,service_year TEXT,P INTEGER,n INTEGER)""")
    con.executemany("INSERT INTO code_profile VALUES(?,?,?,?,?,?)",[
        ("ICD-10-PCS","B020ZZZ","INDEX_IMP","2017",0,16),
        ("ICD-10-PCS","B328ZZZ","INDEX_IMP","2017",0,35),
        ("ICD-10-PCS","B030ZZZ","INDEX_IMP","2017",1,22),
        ("ICD-10-PCS","B33RZZZ","NONIMP_DAY0","2021",0,14),
        ("ICD-10-PCS","B330ZZZ","INDEX_IMP","2021",1,19),
        ("CPT","70450","INDEX_IMP","2017",0,100)])
    con.commit()
    con.close()
    bands=s76.b_source_counts(db,fake_step74)
    assert bands[("2017","0","INDEX_IMP")]==51
    assert bands[("2017","1","INDEX_IMP")]==22
    assert bands[("2021","0","NONIMP_DAY0")]==14
    assert sum(bands.values())==106
    con=sqlite3.connect(str(db))
    con.execute("""UPDATE code_profile SET n=18
       WHERE code='B330ZZZ'""")
    con.commit()
    con.close()
    with pytest.raises(ValueError,match="source counts changed"):
        s76.b_source_counts(db,fake_step74)


def test_console_does_not_leak_exact_private_code(fake_step74,titles,capsys):
    counts,queue=s76.assess(fake_step74,titles)
    b={("2017","0","INDEX_IMP"):51,
       ("2017","1","INDEX_IMP"):22,
       ("2021","0","NONIMP_DAY0"):14,
       ("2021","1","INDEX_IMP"):19}
    s76.print_audit(counts,queue,fake_step74,b)
    out=capsys.readouterr().out
    assert "Candidate_exact_codes 5" in out
    assert "candidate_per_B_source_row_pct" in out
    assert "ANATOMY_UNRESOLVED" not in out
    assert "B020ZZZ" not in out
    assert "B330ZZZ" not in out
    assert "private" not in out.lower()
    # No source patients / events exist in 2016 or 2018 synthetic years.
    # Absent sparse-dictionary keys must be treated as zero, not KeyError.
    assert "2016-2018 review_only_candidates 73 all_B_section_source_rows 73" in out
    assert "2019-2021 review_only_candidates 19 all_B_section_source_rows 19" in out


def test_report_rejects_review_numerator_larger_than_B_source(
        fake_step74,titles,capsys):
    counts,queue=s76.assess(fake_step74,titles)
    # Malformed/misaligned counter summaries must never yield a percentage
    # above 100, even with missing year/P strata.
    missing_B={("2017","0","INDEX_IMP"):50,
               ("2017","1","INDEX_IMP"):20}
    with pytest.raises(ValueError,match="exceed B-section source rows"):
        s76.print_audit(counts,queue,fake_step74,missing_B)
