"""Fabricated Step75 section-B denominator/Step74 reconciliation tests."""
from collections import Counter
import json
import zipfile
from io import BytesIO

import pytest

from scripts import step75_pcs_section_denominator_audit as s75


@pytest.fixture
def cms():
    # Match the Step74 production contract: all FY2016-2025 catalogs
    # are available, even when synthetic source rows use only 2019.
    # This is a fully fabricated source, not a copy of any CMS file.
    fake_titles={
        "B020ZZZ":"Computerized Tomography of Brain",
        "B030ZZZ":"Magnetic Resonance Imaging of Brain",
        "B240ZZZ":"Ultrasonography of Heart",
    }
    return {year:dict(fake_titles) for year in s75.s74.FY}


@pytest.fixture
def source():
    return [
       ("0JH60BZ","INDEX_IMP","2019",0,40),
       ("B020ZZZ","INDEX_IMP","2019",0,14),
       ("B030ZZZ","INDEX_IMP","2019",0,8),
       ("B240ZZZ","INDEX_IMP","2019",0,12),
       ("B999ZZZ","INDEX_IMP","2019",0,6),
       ("B0I0ZZZ","INDEX_IMP","2019",0,3),
       ("B020ZZZ","NONIMP_DAY0","2019",1,17),
       ("0BH17EZ","NONIMP_DAY0","2019",1,12),
       ("B03ZZZZ","UNIQUE_ED","2019",1,1),
    ]


def test_correct_all_PCS_and_B_section_denominator(source,cms):
    counts,reasons=s75.audit_rows(source,cms)
    x=counts[(2019,0,"INDEX_IMP")]
    assert x["all_PCS_rows"]==83
    assert x["non_B_rows"]==40
    assert x["B_rows"]==43
    assert x["B_bad_shape"]==3
    assert x["B_valid_shape"]==40
    assert x["B_matched_neighbor_FY"]==34
    assert x["B_unmatched_neighbor_FY"]==6
    assert x["B_matched_review_only"]==22
    assert x["REVIEW_CNS_CT_rows"]==14
    assert x["REVIEW_CNS_MR_rows"]==8
    assert x["B_matched_not_candidate"]==12
    assert reasons[("INDEX_IMP","NOT_IN_NEIGHBOR_FY")]["B99"]==6
    assert reasons[("INDEX_IMP","BAD_SHAPE")]["B0I"]==3
    assert x["B_matched_neighbor_FY"]/x["B_rows"] == pytest.approx(34/43)
    assert x["B_matched_neighbor_FY"]/x["all_PCS_rows"] == pytest.approx(34/83)


def test_reconciles_to_prior_Step74_counts(source,cms):
    groups,_=s75.audit_rows(source,cms)
    ref={"source_row_aggregates_LOCAL_ONLY":{}}
    for key,summary in groups.items():
        label="|".join(map(str,key))
        ref["source_row_aggregates_LOCAL_ONLY"][label]={
          "source_rows":summary["all_PCS_rows"],
          "in_at_least_one_neighbor_FY_rows":
             summary["B_matched_neighbor_FY"],
          "REVIEW_ONLY_potential_neuroimaging_source_rows":
             summary["B_matched_review_only"]}
    assert s75.verify(None,ref,groups)
    k="2019|0|INDEX_IMP"
    ref["source_row_aggregates_LOCAL_ONLY"][k]["source_rows"]+=1
    with pytest.raises(ValueError,match="does not reconcile"):
        s75.verify(None,ref,groups)


def test_missing_group_and_partition_detection(source,cms):
    groups,_=s75.audit_rows(source,cms)
    ref={"source_row_aggregates_LOCAL_ONLY":{}}
    for key,summary in groups.items():
        ref["source_row_aggregates_LOCAL_ONLY"]["|".join(map(str,key))]={
            "source_rows":summary["all_PCS_rows"],
            "in_at_least_one_neighbor_FY_rows":
                summary["B_matched_neighbor_FY"],
            "REVIEW_ONLY_potential_neuroimaging_source_rows":
                summary["B_matched_review_only"]}
    clone={"source_row_aggregates_LOCAL_ONLY":dict(
        ref["source_row_aggregates_LOCAL_ONLY"])}
    del clone["source_row_aggregates_LOCAL_ONLY"]["2019|1|NONIMP_DAY0"]
    with pytest.raises(ValueError,match="missing"):
        s75.verify(None,clone,groups)
    groups[(2019,0,"INDEX_IMP")]["B_rows"]+=1
    with pytest.raises(AssertionError,match="partition"):
        s75.verify(None,ref,groups)


def test_no_source_strings_in_printed_report(source,cms,capsys):
    summary,reason=s75.audit_rows(source,cms)
    s75.show(summary,reason,cms)
    out=capsys.readouterr().out
    assert "B_section" in out
    assert "B_CMS_match_pct" in out
    assert "REVIEW_CNS_CT" in out
    assert "B020ZZZ" not in out
    assert "0JH60BZ" not in out
    assert "source procedure rows" in out
    assert "FY 2016 B_section_code_titles 3" in out
    assert "FY 2025 B_section_code_titles 3" in out
    assert s75.safe(0)=="0"
    assert s75.safe(1)=="<11"


def test_incomplete_cms_catalog_is_explicit_failure_before_print(source,cms,capsys):
    counts,reasons=s75.audit_rows(source,cms)
    partial={year:titles for year,titles in cms.items() if year>=2019}
    with pytest.raises(ValueError,match="CMS FY catalog incomplete"):
        s75.show(counts,reasons,partial)
    assert capsys.readouterr().out==""


def test_only_realistic_PCS_shape_is_accepted():
    for code in ("B020ZZZ","B030ZZZ","B320ZZZ","0123456"):
        assert s75.VALID_PCS.fullmatch(code)
    for code in ("B0I0ZZZ","B0O0ZZZ","B02","B02.ZZZ",""):
        assert not s75.VALID_PCS.fullmatch(code)


def test_rejects_invalid_profile_rows(cms):
    for bad in [
         [("B020ZZZ","INDEX_IMP","2019",9,7)],
         [("B020ZZZ","INDEX_IMP","2019",0,-2)],
    ]:
        with pytest.raises(ValueError,match="Malformed"):
            s75.audit_rows(bad,cms)
