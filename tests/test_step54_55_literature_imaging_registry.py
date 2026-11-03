"""Synthetic Step54/55 evidence registry checks; no TriNetX source data."""
import csv
import io
import json
import tempfile
from pathlib import Path

import pytest

from scripts.step42_neuroimaging_vocabulary import CPT_ANCHORS
from scripts.step54_literature_imaging_registry import (
    BASE_CPT, classify_imaging_code, research_network_period_policy,
    registry_summary, CPT_HISTORICAL
)
from scripts import step55_private_literature_codebook_review as m
from scripts.step46_47_imaging_review_bundle import (
    PHASE1, INVENTORY, STATUS, REVIEW_COLS
)


@pytest.mark.parametrize("code,expected", sorted(CPT_ANCHORS.items()))
def test_all_historical_CPT14_anchors_match_official_modalities(code,expected):
    assert BASE_CPT[code][0] == expected
    result=classify_imaging_code("CPT",code)
    assert result["category"] == expected
    assert result["status"]=="core_exact_CPT_modality_candidate"
    assert result["source_url"]==CPT_HISTORICAL
    assert result["performed_procedure_verified"] is False
    assert result["clinical_codebook_signed_off"] is False
    assert result["external_code_meaning_supported"] is True
    assert result["source_semantics_verified"] is False


def test_all_categories_and_exact_code_count():
    assert len(BASE_CPT)==14
    assert registry_summary()["historical_core_codes"]==14
    assert registry_summary()["performed_procedure_verified"] is False
    assert set(registry_summary()["study_outcomes"]) == {
        "CT_HEAD", "CTA_HEAD", "CTA_NECK",
        "MRI_BRAIN", "MRA_HEAD", "MRA_NECK",
    }


@pytest.mark.parametrize("code",[
    "70554", "70555", "70540", "70542", "70543",
    "70480", "70486", "70490", "70491", "93880", "93882",
])
def test_wrong_anatomy_and_functional_imaging_cannot_count(code):
    result=classify_imaging_code("CPT",code)
    assert result["status"]=="exclude_not_study_modality"
    assert result["category"] is None


def test_non_CPT_code_does_not_inherit_identical_digits():
    for system in ("SNOMED","HCPCS","ICD-10-PCS","ICD-9-CM"):
        result=classify_imaging_code(system,"70551")
        assert result["status"]=="defer_unmapped_or_unverified_system"
        assert result["category"] is None
        assert result["source_semantics_verified"] is False


def test_new_2026_combined_CTA_is_not_silently_just_head():
    result=classify_imaging_code("CPT","70471","2026-02-01")
    assert result["status"]=="extended_CTA_head_plus_neck_2026_only_NOT_CORE"
    assert result["category"]=="CTA_HEAD"
    assert result["secondary_category"]=="CTA_NECK"
    assert result["date_compatibility"]=="yes"
    assert result["performed_procedure_verified"] is False
    assert classify_imaging_code("CPT","70471","2025-12-31")["date_compatibility"]=="no_before_2026"
    assert classify_imaging_code("CPT","70471")["date_compatibility"]=="unknown_requires_date"


@pytest.mark.parametrize("code,d,expected",[
    ("0042T","2025-12-31","yes"),
    ("0042T","2026-01-01","no_outside_valid_era"),
    ("70472","2025-12-31","no_outside_valid_era"),
    ("70473","2025-12-31","no_outside_valid_era"),
    ("70472","2026-01-01","yes"),
    ("70473","2026-01-01","yes"),
])
def test_CT_perfusion_code_era_never_conflated_with_CTA(code,d,expected):
    result=classify_imaging_code("CPT",code,d)
    assert result["status"].startswith("CT_PERFUSION_SEPARATE")
    assert result["category"] is None
    assert result["date_compatibility"]==expected


def test_research_network_and_diamond_independent_periods():
    p=research_network_period_policy()
    assert p["diamond"] == {
        "start":"2018-01-01", "end":"2019-12-31", "period_fixed":True,
    }
    assert p["research_network"]["proposed_start"]=="2016-01-01"
    assert p["research_network"]["proposed_end"] is None
    assert p["research_network"]["2018_2019_Diamond_rule_must_NOT_be_reused"] is True


def fake_row(n, system, code, description):
    return {
        "review_id":f"{n:064x}",
        "code_system":system, "code":code,
        "reference_description":description, "reference_path":"",
        "automated_candidate_NOT_APPROVED":"MRI_BRAIN",
    }


def test_private_adjudication_preserves_legacy_identity_without_auto_signoff():
    source=[
        fake_row(1,"CPT","70551","MRI brain"),
        fake_row(2,"SNOMED","70551","MRI brain"),
        fake_row(3,"CPT","70496","CT angiography head"),
        fake_row(4,"CPT","70554","Functional MRI brain"),
    ]
    dispositions=m.review_reference_rows(source)
    assert len(dispositions)==4
    assert dispositions[0]["literature_status"]=="core_exact_CPT_modality_candidate"
    assert dispositions[0]["literature_category"]=="MRI_BRAIN"
    assert dispositions[1]["literature_status"]=="defer_unmapped_or_unverified_system"
    assert dispositions[2]["literature_category"]=="CTA_HEAD"
    assert dispositions[3]["literature_status"]=="exclude_not_study_modality"
    assert all(row["procedure_record_performed_NOT_VERIFIED"]=="NOT_VERIFIED"
               for row in dispositions)
    assert all(row["local_code_mapping_NOT_VERIFIED"]=="NOT_VERIFIED"
               for row in dispositions)


def test_clear_source_terminology_contradiction_is_held():
    rows=[fake_row(1,"CPT","70551","CT chest")]
    x=m.review_reference_rows(rows)[0]
    assert x["reference_term_conflict_flag"]=="yes"
    assert x["literature_category"]==""
    assert x["literature_status"].startswith("hold_CPT")


def test_empty_or_duplicated_identity_fails_closed():
    x=fake_row(1,"CPT","70551","MRI brain")
    with pytest.raises(ValueError, match="Duplicate"):
        m.review_reference_rows([x,x])
    x["review_id"]="not-valid-id"
    with pytest.raises(ValueError, match="hashed"):
        m.review_reference_rows([x])


@pytest.fixture
def private_synthetic_workspace():
    PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step55_reference_synthetic_",dir=PHASE1) as dirname:
        home=Path(dirname)
        source=home/"old_imaging_review"
        source.mkdir(mode=0o700)
        output=home/"literature_review"
        yield source,output


def make_legacy_inventory(source, rows):
    with (source/INVENTORY).open("w", newline="", encoding="utf-8") as out:
        writer=csv.DictWriter(out,fieldnames=REVIEW_COLS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                **{key:"" for key in REVIEW_COLS},
                **row,
            })
    status={
        "stage":"STEP46_PRIVATE_IMAGING_REVIEW_PREPARED",
        "clinical_event_rows_read":0,
        "codebook_clinically_validated":False,
        "full_reference_candidate_entries_preserved":len(rows),
    }
    (source/STATUS).write_text(json.dumps(status))


def test_private_literature_report_no_overwrite_no_approval(private_synthetic_workspace):
    src,dest=private_synthetic_workspace
    rows=[
        fake_row(1,"CPT","70551","MRI brain"),
        fake_row(2,"CPT","70496","CTA head"),
        fake_row(3,"SNOMED","121","Uncertain anatomy"),
    ]
    make_legacy_inventory(src,rows)
    before=(src/INVENTORY).read_bytes()
    result=m.prepare(src,dest)
    assert (src/INVENTORY).read_bytes()==before
    assert result["reference_rows_examined"]==3
    assert result["unique_CPT14_anchors_located"]==2
    assert result["clinical_event_rows_read"]==0
    assert result["codebook_signed_off"] is False
    assert result["performed_procedure_meaning_approved"] is False
    assert result["research_network_period_policy"]["proposed_end"] is None
    assert (dest/m.CORE_MATCHES).stat().st_mode & 0o077 == 0
    assert (dest/m.DISPOSITIONS).stat().st_mode & 0o077 == 0
    assert dest.stat().st_mode & 0o077 == 0
    assert "Uncertain anatomy" not in (dest/m.DISPOSITIONS).read_text()
    with pytest.raises(FileExistsError,match="already exist"):
        m.prepare(src,dest)


def test_prior_signed_or_clinical_rows_claim_fails(private_synthetic_workspace):
    src,dest=private_synthetic_workspace
    make_legacy_inventory(src,[fake_row(1,"CPT","70551","MRI brain")])
    status=json.loads((src/STATUS).read_text())
    status["clinical_event_rows_read"]=12
    (src/STATUS).write_text(json.dumps(status))
    with pytest.raises(ValueError,match="safe reference-only"):
        m.prepare(src,dest)
    assert not dest.exists()


def test_local_clinical_source_not_required_for_external_code_meaning():
    assert classify_imaging_code("CPT","70551")["external_code_meaning_supported"] is True
    assert classify_imaging_code("CPT","70551")["source_semantics_verified"] is False
    assert classify_imaging_code("CPT","70551")["performed_procedure_verified"] is False


def test_unknown_CPT_is_not_claimed_to_have_verified_external_meaning():
    candidate=classify_imaging_code("CPT","99999")
    assert candidate["status"]=="defer_CPT_not_in_literature_core"
    assert candidate["source_semantics_verified"] is False
    assert candidate["external_code_meaning_supported"] is False
    assert candidate["performed_procedure_verified"] is False


def test_CMS_carotid_duplex_exclusion_has_specific_external_reference():
    candidate=classify_imaging_code("CPT","93880")
    assert candidate["category"] is None
    assert candidate["status"]=="exclude_not_study_modality"
    assert "cms.gov" in candidate["source_url"]
    assert "2014-physician-fee-schedule" in candidate["source_url"]


def test_public_literature_code_meaning_table_matches_the_versioned_registry():
    path=Path(__file__).resolve().parents[1] / (
        "docs/STEP54_PUBLIC_CPT14_LITERATURE_CODE_MEANING_REVIEW.csv"
    )
    with path.open(newline="",encoding="utf-8") as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==14
    observed={(row["code_system"],row["code"]):row for row in rows}
    assert set(observed)=={("CPT",code) for code in BASE_CPT}
    for code, (category,meaning) in BASE_CPT.items():
        row=observed[("CPT",code)]
        assert row["modality_category"]==category
        assert row["meaning_review_decision"]=="evidence_supported_exact_code"
        assert row["source_event_performed_verification"]=="not_verified_locally"
        assert row["external_evidence_url"]==CPT_HISTORICAL
