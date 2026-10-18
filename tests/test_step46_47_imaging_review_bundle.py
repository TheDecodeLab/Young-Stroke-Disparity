"""Steps 46-47 synthetic-only reviewer packet tests, no real clinical data."""
from __future__ import annotations

import csv
import io
import json
import tempfile
from collections import Counter
from pathlib import Path

import pytest

from scripts import step46_47_imaging_review_bundle as m


@pytest.fixture
def sandbox():
    m.PHASE1.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step46_synthetic_", dir=m.PHASE1) as tmp:
        folder = Path(tmp)
        review = folder / "private_review"
        review.mkdir(mode=0o700)
        source = folder / "step42_private.csv"
        summary = folder / "step42_private.json"
        target = folder / "full_reconstruction_private" / "imaging_codebook_APPROVED_LOCAL_ONLY.csv"
        return folder, source, summary, review, target


def build_source(source, summary):
    records = [
        ("CPT", "70551", "MR imaging of brain", "", "MRI_BRAIN", "historical_cpt14_anchor"),
        ("CPT", "70496", "CT angiography, head", "", "CTA_HEAD", "historical_cpt14_anchor"),
        ("CPT", "70498", "CT angiography, neck", "", "CTA_NECK", "historical_cpt14_anchor"),
        ("SNOMED", "77881", "Magnetic resonance imaging of brain", "", "MRI_BRAIN", "textual_candidate"),
        ("SNOMED", "88221", "CTA head and neck", "", "AMBIGUOUS_HEAD_AND_NECK", "textual_candidate_needs_anatomy_review"),
        ("SNOMED", "88222", "=HYPERLINK('x') of brain MRI", "", "MRI_BRAIN", "textual_candidate"),
        ("SNOMED", "88223", "CT head", "", "CT_HEAD", "textual_candidate"),
        ("HCPCS", "A0001", "Magnetic resonance angiography of neck", "", "MRA_NECK", "textual_candidate"),
    ]
    with source.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=m.REQUIRED_SOURCE)
        w.writeheader()
        for system,code,desc,path,cat,reason in records:
            w.writerow({
                "code_system":system,"code":code,"code_description":desc,"path":path,
                "candidate_category_NOT_VALIDATED":cat,"discovery_reason":reason,
                "reviewer_include_LEAVE_BLANK":"","reviewer_notes_LEAVE_BLANK":"",
            })
    status={
        "stage":m.STAGE,
        "source_is_reference_terminology_only":True,
        "clinical_event_rows_examined":0,
        "candidate_rows_n":len(records),
        "candidate_category_rows":dict(Counter(r[4] for r in records)),
        "discovery_reason_rows":dict(Counter(r[5] for r in records)),
    }
    summary.write_text(json.dumps(status))


def read_priority(path):
    with path.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mark_valid_review(row):
    row["clinician_decision_INCLUDE_EXCLUDE_DEFER"]="include"
    row["reviewed_category"]="MRI_BRAIN"
    row["performed_procedure_confirmed_yes_no"]="yes"
    row["valid_for_2018_2019_yes_no"]="yes"
    row["anatomy_resolved_yes_no"]="yes"
    row["clinical_rationale"]="Authorized code meaning verified for MRI brain"
    row["evidence_reference"]="LOCAL_CLINICAL_DEFINITION_1"
    row["reviewer"]="Test Clinician"
    row["review_date"]="2026-10-17"


def write_review(path,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,m.REVIEW_COLS)
        w.writeheader()
        w.writerows(rows)


def sign(review):
    path=review/m.SIGNOFF
    d=json.loads(path.read_text())
    d.update({name:True for name in m.SIGNOFF_FIELDS})
    d.update({"reviewer_name":"Test Clinician","review_date":"2026-10-17",
              "review_authority_reference":"TEST_INTERNAL","scope_notes":"Reviewed all candidate inventory categories and terminology provenance"})
    path.write_text(json.dumps(d))


def test_prepare_preserves_all_candidates_and_makes_compact_review(sandbox):
    folder,source,summary,review,target=sandbox
    build_source(source,summary)
    before=source.read_bytes()
    result=m.prepare(source,summary,review,per_category=1,ambiguous_limit=1)
    assert result["clinical_event_rows_read"]==0
    assert result["full_reference_candidate_entries_preserved"]==8
    assert result["historical_CPT_anchors_for_verification"]==3
    assert (review/m.QUESTIONS).exists()
    assert source.read_bytes()==before
    assert len(read_priority(review/m.INVENTORY))==8
    prioritized=read_priority(review/m.PRIORITY)
    assert len(prioritized)==7
    assert len({r["review_id"] for r in prioritized})==len(prioritized)
    assert all(not r["clinician_decision_INCLUDE_EXCLUDE_DEFER"] for r in prioritized)
    assert "'" + "=HYPERLINK" in (review/m.INVENTORY).read_text()
    assert all(json.loads((review/m.SIGNOFF).read_text())[k] is False for k in m.SIGNOFF_FIELDS)
    assert not target.exists()
    for name in (m.INVENTORY,m.PRIORITY,m.QUESTIONS,m.SIGNOFF,m.STATUS):
        assert (review/name).stat().st_mode & 0o077 == 0


def test_prepare_does_not_overwrite_human_annotations(sandbox):
    _,source,summary,review,_=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    annotated=review/m.PRIORITY
    annotated.write_text("DO_NOT_ERASE_REVIEW")
    with pytest.raises(FileExistsError,match="erase clinical annotations"):
        m.prepare(source,summary,review)
    assert annotated.read_text()=="DO_NOT_ERASE_REVIEW"


@pytest.mark.parametrize("break_field",["candidate_rows_n","clinical_event_rows_examined","candidate_category_rows"])
def test_source_lineage_or_totals_fail_closed(sandbox,break_field):
    _,source,summary,review,_=sandbox
    build_source(source,summary)
    obj=json.loads(summary.read_text())
    if break_field=="candidate_rows_n":obj[break_field]+=1
    elif break_field=="clinical_event_rows_examined":obj[break_field]=7
    else:obj[break_field]["MRI_BRAIN"]+=1
    summary.write_text(json.dumps(obj))
    with pytest.raises(ValueError):
        m.prepare(source,summary,review)
    assert not (review/m.PRIORITY).exists()


def test_finalize_with_blank_attestation_is_blocked(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    with pytest.raises(PermissionError,match="signed review gates incomplete"):
        m.finalize(source,summary,review,target=target)
    assert not target.exists()


def test_signed_reviewer_codebook_creation_keeps_institutional_approvals_untouched(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    rows=read_priority(review/m.PRIORITY)
    chosen=next(r for r in rows if r["code"]=="70551")
    mark_valid_review(chosen)
    write_review(review/m.PRIORITY,rows)
    sign(review)
    target.parent.mkdir(mode=0o700)
    target.write_text(m.FINAL_HEADER)
    approval=target.parent/"approvals_LOCAL_ONLY.json"
    approval.write_text('{"institutional_data_use_approved":false}')
    result=m.finalize(source,summary,review,target=target)
    assert result["included_code_entries"]==1
    assert result["full_scan_executed"] is False
    assert result["step45_institutional_approval_flags_changed"] is False
    assert approval.read_text()=='{"institutional_data_use_approved":false}'
    lines=list(csv.DictReader(target.open()))
    assert len(lines)==1
    assert lines[0]["code_system"]=="CPT"
    assert lines[0]["code"]=="70551"
    assert lines[0]["record_meaning"]=="performed"
    assert "70551" not in (review/m.FINAL_STATUS).read_text()
    assert target.stat().st_mode & 0o077 == 0


def test_include_needs_performed_proof_and_anatomy(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    rows=read_priority(review/m.PRIORITY)
    chosen=next(r for r in rows if r["code"]=="70551")
    mark_valid_review(chosen)
    chosen["performed_procedure_confirmed_yes_no"]="no"
    write_review(review/m.PRIORITY,rows)
    sign(review)
    with pytest.raises(PermissionError,match="performed meaning"):
        m.finalize(source,summary,review,target=target)
    assert not target.exists()


def test_mixed_anatomy_cannot_be_included_without_rationale(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    rows=read_priority(review/m.PRIORITY)
    chosen=next(r for r in rows if r["code"]=="88221")
    mark_valid_review(chosen)
    chosen["clinical_rationale"]="short"
    write_review(review/m.PRIORITY,rows)
    sign(review)
    with pytest.raises(PermissionError,match="substantial clinical rationale"):
        m.finalize(source,summary,review,target=target)


def test_change_of_code_key_or_unknown_id_fails_closed(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    rows=read_priority(review/m.PRIORITY)
    rows[0]["code"]="FAKE_CODE"
    write_review(review/m.PRIORITY,rows)
    sign(review)
    with pytest.raises(ValueError,match="provenance mismatch"):
        m.finalize(source,summary,review,target=target)
    assert not target.exists()


def test_existing_nonempty_codebook_never_overwritten(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    rows=read_priority(review/m.PRIORITY)
    mark_valid_review(next(r for r in rows if r["code"]=="70551"))
    write_review(review/m.PRIORITY,rows)
    sign(review)
    target.parent.mkdir(mode=0o700)
    target.write_text(m.FINAL_HEADER+"CPT,12345,CTA_HEAD,performed,Clinician,2026-10-17\n")
    original=target.read_text()
    with pytest.raises(FileExistsError,match="never overwrite manual changes"):
        m.finalize(source,summary,review,target=target)
    assert target.read_text()==original


def test_no_outputs_outside_ignored_results(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    with pytest.raises(ValueError,match="results/phase1"):
        m.prepare(source,summary,Path("/tmp/step46_outside"))
    with pytest.raises(ValueError,match="results/phase1"):
        m.finalize(source,summary,review,target=Path("/tmp/step46_unapproved.csv"))



def test_protected_reference_description_cannot_be_rewritten(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    rows=read_priority(review/m.PRIORITY)
    rows[0]["reference_description"]="Misleading manually changed code description"
    write_review(review/m.PRIORITY,rows)
    sign(review)
    with pytest.raises(ValueError,match="Protected reference metadata"):
        m.finalize(source,summary,review,target=target)
    assert not target.exists()


def test_clinician_reviewer_formula_is_not_exported(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    rows=read_priority(review/m.PRIORITY)
    included=next(r for r in rows if r["code"]=="70551")
    mark_valid_review(included)
    included["reviewer"]="=HYPERLINK('unsafe')"
    write_review(review/m.PRIORITY,rows)
    sign(review)
    with pytest.raises(ValueError,match="Unsafe reviewer"):
        m.finalize(source,summary,review,target=target)
    assert not target.exists()


def test_review_signoff_is_bound_to_source_status_digest(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    rows=read_priority(review/m.PRIORITY)
    mark_valid_review(next(r for r in rows if r["code"]=="70551"))
    write_review(review/m.PRIORITY,rows)
    sign(review)
    current=json.loads((review/m.SIGNOFF).read_text())
    current["source_step42_status_sha256"]="mismatch"
    (review/m.SIGNOFF).write_text(json.dumps(current))
    with pytest.raises(PermissionError,match="source changed"):
        m.finalize(source,summary,review,target=target)


def test_complete_inventory_may_be_reviewed_without_auto_including_any_code(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    full=review/m.INVENTORY
    rows=read_priority(full)
    mark_valid_review(next(r for r in rows if r["code"]=="70551"))
    write_review(full,rows)
    sign(review)
    result=m.finalize(source,summary,review, review=full, target=target)
    assert result["included_code_entries"]==1



def test_source_csv_edit_after_preparation_requires_new_review(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    rows=read_priority(review/m.PRIORITY)
    mark_valid_review(next(r for r in rows if r["code"]=="70551"))
    write_review(review/m.PRIORITY,rows)
    sign(review)
    # Preserve row/category counts but alter a distinct source code description.
    lines=source.read_text()
    assert "CT head" in lines
    source.write_text(lines.replace("CT head","CT of the head"))
    with pytest.raises(PermissionError,match="source changed"):
        m.finalize(source,summary,review,target=target)
    assert not target.exists()


def test_review_row_date_cannot_postdate_signoff(sandbox):
    _,source,summary,review,target=sandbox
    build_source(source,summary)
    m.prepare(source,summary,review)
    rows=read_priority(review/m.PRIORITY)
    item=next(r for r in rows if r["code"]=="70551")
    mark_valid_review(item)
    item["review_date"]="2026-10-18"
    write_review(review/m.PRIORITY,rows)
    sign(review)
    with pytest.raises(PermissionError,match="after signed clinical review"):
        m.finalize(source,summary,review,target=target)
