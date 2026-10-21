"""Synthetic-only Step80 full manuscript and release gate regression tests."""
from copy import deepcopy
import json
from pathlib import Path
import re

import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step78_paper_results_bundle as s78
from scripts import step80_finalize_manuscript_local as s80


def fabricated_tables():
    t1=[]
    for cohort in s62.COHORTS:
        for p,n,im,held in ((0,400,160,120),(1,250,70,90)):
            t1.append(dict(
                cohort=cohort,P_indicator=p,denominator=n,
                any_ambiguous_encounter_patient_n=held,
                any_ambiguous_encounter_patient_pct=100*held/n,
                index_inpatient_CPT14_n=im,
                index_inpatient_CPT14_pct=100*im/n))
    t2=[]
    for cohort in s62.COHORTS:
        for key,vals in (
            ("INDEX_IMP",(160,70)),
            ("INDEX_IMP_OR_SAME_DAY_OTHER",(210,155)),
            ("INDEX_IMP_OR_UNIQUE_ED",(174,78)),
            ("INDEX_IMP_OR_ED_PRE2_DAY0",(246,186))
        ):
            p0,p1=100*vals[0]/400,100*vals[1]/250
            t2.append({
                "cohort":cohort,"endpoint_key":key,
                "P0_n":400,"P1_n":250,
                "P0_documented_code_n":vals[0],
                "P1_documented_code_n":vals[1],
                "P0_crude_pct":p0,"P1_crude_pct":p1,
                "P1_minus_P0_crude_pp":p1-p0,
                "P1_minus_P0_common_year_quarantine_pp":(p1-p0)-1.5,
                "P1_minus_P0_common_year_only_pp":(p1-p0)-0.6,
                "P1_minus_P0_no_ambiguous_pp":(p1-p0)+0.1,
                "actual_imaging_performed_verified":False,
                "HCO_episode_verified":False,
            })
    return {"t1":t1,"t2":t2}


def test_manuscript_quantitative_results_use_frozen_aggregate_inputs():
    tables=fabricated_tables()
    values,rows=s80.extract(tables)
    assert len(rows)==4
    assert "650 indexed" in values["ABSTRACT_RESULTS"]
    assert "160" in values["RESULTS_TEXT"]
    assert "155" in values["RESULTS_TEXT"]
    assert "Table 2." in values["RESULTS_TEXT"]
    assert "CPT14" in values["RESULTS_TEXT"]
    assert "not confirmed" in values["RESULTS_TEXT"].lower()
    assert "Table 4" not in values["RESULTS_TEXT"]


def test_draft_complete_and_matches_verifiable_portable_citations():
    refs=json.loads(s80.CSL.read_text(encoding="utf-8"))
    template=s80.TEMPLATE.read_text(encoding="utf-8")
    text=s80.fill_template(template,s80.extract(fabricated_tables())[0],refs)
    assert "{{ABSTRACT_RESULTS}}" not in text
    assert "{{RESULTS_TEXT}}" not in text
    for section in ("## Abstract","## Introduction","## Methods",
                    "## Results","## Discussion","## Conclusion",
                    "## References"):
        assert section in text
    assert "NOT CLEARED FOR EXTERNAL DISCLOSURE" in text
    assert "Table 4 (WITHHELD)" in text
    assert len(re.findall(r"^\d+\. ",text,flags=re.M))==9
    assert "10.1093/jamia/ocad120" in text
    assert "10.3390/jcm12072600" in text
    assert "10.1242/dmm.048785" in text


def test_missing_manuscript_citation_fails_closed():
    refs=json.loads(s80.CSL.read_text(encoding="utf-8"))
    template=s80.TEMPLATE.read_text(encoding="utf-8")
    with pytest.raises(ValueError,match="missing from portable"):
        s80.fill_template(template+" [@Nonexistent2033]",
                          s80.extract(fabricated_tables())[0],refs)


def test_figure2_uses_unconnected_dots_and_outputs_are_local(tmp_path):
    _,rows=s80.extract(fabricated_tables())
    s80.figures(rows,tmp_path)
    for name in ("figure1_code_capture_review_v1.png",
                 "figure2_unconnected_contrasts_review_v1.png"):
        p=tmp_path/name
        assert p.exists() and p.stat().st_size>1200
        with p.open("rb") as fh:
            assert fh.read(8)==b"\x89PNG\r\n\x1a\n"
    source=Path(s80.__file__).read_text(encoding="utf-8")
    plotting=source[source.index("def figures("):source.index("def disclosure_packet(")]
    assert "ax.plot(" not in plotting
    assert "ax.scatter(" in plotting


def test_disclosure_packet_has_no_source_counts_and_requires_review():
    packet=s80.disclosure_packet()
    assert "PENDING" in packet
    assert "Step79" in packet
    assert "minimum-cell" in packet
    assert "Table 4" in packet
    assert "approval" in packet.lower()
    assert "64,721" not in packet


def test_wrong_index_denominator_or_missing_endpoint_refused():
    tables=fabricated_tables()
    broken=deepcopy(tables)
    broken["t2"][0]["P0_n"]+=1
    with pytest.raises(ValueError,match="cohort denominator"):
        s80.extract(broken)
    broken=deepcopy(tables)
    broken["t2"]=[r for r in broken["t2"] if not (
        r["cohort"]==s78.PRIMARY and
        r["endpoint_key"]=="INDEX_IMP_OR_UNIQUE_ED")]
    with pytest.raises(ValueError,match="missing endpoint"):
        s80.extract(broken)
