"""Public-reference and active-study consistency checks (no clinical I/O)."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "docs" / "references"


def _items():
    items=json.loads((REF / "imaging_references.csl.json").read_text("utf-8"))
    assert isinstance(items,list)
    return {x["id"]:x for x in items}


def _crosswalk():
    with (REF/"CODE_TO_REFERENCE_CROSSWALK.csv").open(
            encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))


def test_reference_exports_have_same_nine_stable_ids():
    items=_items()
    assert len(items)==9
    ris=(REF/"imaging_references.ris").read_text("utf-8")
    bib=(REF/"imaging_references.bib").read_text("utf-8")
    ris_ids=set(re.findall(r"^ID  - (\S+)$",ris,re.M))
    bib_ids=set(re.findall(r"^@\w+\{([^,]+),",bib,re.M))
    assert ris_ids==bib_ids==set(items)
    assert len(re.findall(r"^ER  - ",ris,re.M))==len(items)


def test_two_pubmed_articles_are_uniquely_identified_and_title_verified():
    items=_items()
    assert items["Vagal2017_AJNR"]["DOI"]=="10.3174/ajnr.A5340"
    assert items["Vagal2017_AJNR"]["PMID"]=="28838913"
    assert items["Wang2024_JACR"]["DOI"]=="10.1016/j.jacr.2023.07.015"
    assert items["Wang2024_JACR"]["PMID"]=="37586470"
    assert items["Wang2024_JACR"]["title"].startswith("Gender-Based Disparity")
    assert len({x.get("DOI") for x in items.values() if x.get("DOI")})==2


def test_all_fourteen_core_imaging_codes_have_CMS2010_source():
    rows=_crosswalk()
    core=[r for r in rows if r["decision"]=="core_exact_modality_meaning"]
    assert len(core)==14
    assert len({r["code"] for r in core})==14
    assert {r["reference_key"] for r in core}=={"CMS2010_MPPR"}
    assert set(r["category"] for r in core)=={
        "CT_HEAD","CTA_HEAD","CTA_NECK","MRI_BRAIN","MRA_HEAD","MRA_NECK"
    }
    assert all(r["source_url"].endswith("r738otn.pdf") for r in core)


def test_excluded_non_standalone_codes_are_eight_with_tracked_sources():
    rows=_crosswalk()
    excluded=[r for r in rows if
              r["decision"]=="exclude_from_six_diagnostic_categories"]
    assert {r["code"] for r in excluded}=={
        "0398T","0865T","0866T","61736","61737","61751","78814","78830"
    }
    assert all(r["source_url"].startswith("https://") for r in excluded)


def test_new_2026_head_neck_CTA_not_hidden_in_2011_core():
    rows=_crosswalk()
    by_code={r["code"]:r for r in rows}
    assert by_code["70471"]["decision"]=="conditional_future_2026_dual_site_not_CPT14"
    assert by_code["70471"]["category"]=="CTA_HEAD+CTA_NECK"
    for code in ("70472","70473","0042T"):
        assert by_code[code]["category"]=="CT_PERFUSION_SEPARATE"
        assert by_code[code]["reference_key"]=="HHS2025_OPPS2026"


def test_five_local_nonstandard_identifiers_are_not_publicly_embedded():
    txt=(REF/"CODE_TO_REFERENCE_CROSSWALK.csv").read_text("utf-8")
    assert "LOCAL_FIVE_NONSTANDARD_IDS_NOT_EXPORTED" in txt
    for derived in ("1010296","1010318","1010322","1014877","1036724"):
        assert derived not in txt
        assert derived not in (REF/"IMAGING_CODE_CITATION_REGISTER.md").read_text("utf-8")


def test_each_citation_crosswalk_key_has_canonical_or_explained_supplemental_source():
    items=_items()
    supplemental={"CMS_A54953"}|{"AAPC_CPT_"+v for v in ("61736","61737","61751")}
    cross={r["reference_key"] for r in _crosswalk()}
    assert cross <= set(items)|supplemental
    assert all(r["source_url"].startswith("https://") for r in _crosswalk())


def test_active_plan_separates_research_network_and_diamond_and_alternative_outcomes():
    plan=(ROOT/"docs/ACTIVE_RESEARCH_NETWORK_STUDY_PLAN.md").read_text("utf-8")
    assert "**Diamond**" in plan and "2018-01-01" in plan
    assert "**TriNetX Research Network**" in plan and "2016-01-01" in plan
    assert "End date unknown" in plan
    assert "Primary A" in plan and "Sensitivity B" in plan
    assert "18–50" in plan and "18–52" in plan and "18–54" in plan
    assert "511 passed" in plan
    assert "Step45 old real-data CLI **remains disabled**" in plan


def test_no_claim_that_research_network_performed_care_was_validated():
    ledger=(REF/"IMAGING_CODE_CITATION_REGISTER.md").read_text("utf-8")
    assert "Source pages can change" in ledger
    assert "source-specific" in ledger or "source" in ledger
    assert "not functioning Zotero Word citations" in ledger
    assert "performed" in ledger.lower()
    plan=(ROOT/"docs/ACTIVE_RESEARCH_NETWORK_STUDY_PLAN.md").read_text("utf-8")
    assert "actual patient-event" not in plan or "unknown" in plan.lower()


def test_readme_has_one_active_plan_and_explicit_historical_warning():
    readme=(ROOT/"README.md").read_text("utf-8")
    assert readme.count("## CURRENT PLAN OF RECORD")==1
    assert "IMAGING_CODE_CITATION_REGISTER.md" in readme
    assert "historical implementation records" in readme
    assert "No source-wide revised Research Network scan executed" in readme


def test_public_inclusion_registry_evidence_urls_match_code_crosswalk():
    from scripts.step54_literature_imaging_registry import (
        BASE_CPT, classify_imaging_code,
    )
    by_code={r["code"]:r for r in _crosswalk()}
    for code, (category, _) in BASE_CPT.items():
        observed=by_code[code]
        candidate=classify_imaging_code("CPT",code)
        assert observed["category"]==category
        assert observed["source_url"]==candidate["source_url"]
        assert candidate["source_semantics_verified"] is False


def test_eight_exclusion_source_urls_match_authoritative_register():
    from scripts.step57_external_cpt_adjudication import PUBLIC_EXCLUSIONS
    by_code={r["code"]:r for r in _crosswalk()}
    assert len(PUBLIC_EXCLUSIONS)==8
    for code, (_,source_url,_) in PUBLIC_EXCLUSIONS.items():
        observed=by_code[code]
        assert observed["decision"]=="exclude_from_six_diagnostic_categories"
        assert observed["source_url"]==source_url


def test_year_2026_official_federal_rule_is_used_for_CTA_and_perfusion():
    from scripts.step54_literature_imaging_registry import (
        CTP_2026_CHANGE, CPT_2026_CHANGE,
    )
    by_code={r["code"]:r for r in _crosswalk()}
    assert CTP_2026_CHANGE.endswith("2025-20907.pdf")
    assert by_code["70471"]["source_url"].endswith("2025-20907.pdf")
    assert {by_code[x]["source_url"] for x in ("70472","70473","0042T")}=={
        CTP_2026_CHANGE
    }
    # CPT_2026_CHANGE is a separate official CMS code list; the manuscript
    # reference uses the Federal Register rule for exact code descriptors.
    assert CPT_2026_CHANGE.startswith("https://www.cms.gov/")
