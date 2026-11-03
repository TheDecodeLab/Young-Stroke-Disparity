"""Synthetic-only Step57 adjudication tests; never touch TriNetX clinical files."""
import csv
import hashlib
import io
import json
import tempfile
from pathlib import Path

import pytest

from scripts import step57_external_cpt_adjudication as m


@pytest.mark.parametrize("code", sorted(m.PUBLIC_EXCLUSIONS))
def test_eight_documented_non_diagnostic_CPT_codes_are_excluded(code):
    result = m.classify(code)
    assert result["decision"] == "exclude_from_six_diagnostic_imaging_categories"
    assert result["evidence_url"].startswith("https://")
    assert result["external_meaning"]
    assert result["source_system_mapping_verified"] == "NOT_VERIFIED"


@pytest.mark.parametrize("code", ["9000001", "9000002", "9000003", "9000004", "9000005"])
def test_seven_digit_private_identifiers_are_held_not_misread_as_CPT(code):
    result = m.classify(code)
    assert result["decision"] == "hold_nonstandard_CPT_shape_CHECK_ORIGINAL_CODE_SYSTEM"
    assert result["source_system_mapping_verified"] == "NOT_VERIFIED"


def test_standard_but_unresearched_CPT_code_remains_deferred():
    r = m.classify("99999")
    assert r["decision"] == "defer_other_CPT_REQUIRES_EXACT_CODE_EVIDENCE"
    assert r["evidence_url"] == ""


def local_record(code, n):
    return {
        **{k: "" for k in m.QUEUE_FIELDS},
        "code_system": "CPT",
        "code": code,
        "step46_review_id": f"{n:064x}",
        "original_terminology_description_LOCAL_ONLY": "SYNTHETIC_TERMINOLOGY_DESCRIPTION",
        "literature_status": "defer_CPT_not_in_literature_core",
    }


def test_review_13_codes_keeps_all_8_exclusions_and_5_holds():
    codes = sorted(m.PUBLIC_EXCLUSIONS) + [
        "9000001", "9000002", "9000003", "9000004", "9000005"
    ]
    rows = m.adjudicate([local_record(c, i) for i, c in enumerate(codes, 1)])
    assert len(rows) == 13
    assert sum(r["external_evidence_decision"] ==
               "exclude_from_six_diagnostic_imaging_categories" for r in rows) == 8
    assert sum(r["external_evidence_decision"] ==
               "hold_nonstandard_CPT_shape_CHECK_ORIGINAL_CODE_SYSTEM" for r in rows) == 5
    assert all(r["approved_for_core_diagnostic_imaging"] == "NO" for r in rows)
    assert all(r["source_event_performed_status_verified"] == "NOT_VERIFIED" for r in rows)


def test_cannot_promote_unrelated_source_or_duplicate_review():
    row = local_record("61751", 1)
    with pytest.raises(ValueError, match="Duplicate"):
        m.adjudicate([row, row])
    with pytest.raises(ValueError, match="provenance"):
        m.adjudicate([{**row, "code_system": "SNOMED"}])
    with pytest.raises(ValueError, match="provenance"):
        m.adjudicate([{**row, "literature_status": "core_exact_CPT_modality_candidate"}])


def test_invalid_review_id_refused():
    row = local_record("61736", 1)
    row["step46_review_id"] = "missing_SHA"
    with pytest.raises(ValueError, match="provenance"):
        m.adjudicate([row])


@pytest.fixture
def private_workspace():
    m.TRIAGE_DIR.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=m.TRIAGE_DIR.parent, prefix="step57_synthetic_"
    ) as p:
        base = Path(p)
        src, dest = base / "step56_synthetic", base / "step57_synthetic"
        src.mkdir(mode=0o700)
        src_row = [local_record("0398T", 1), local_record("9000001", 2)]
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=m.QUEUE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(src_row)
        (src / m.CPT_QUEUE).write_text(buf.getvalue())
        report = {
            "stage": "STEP56_REFERENCE_VOCABULARY_COVERAGE_TRIAGE_ONLY",
            "patient_or_clinical_event_rows_read": 0,
            "Research_Network_ZIP_opened": False,
            "clinical_codebook_approved": False,
            "full_clinical_scan_enabled": False,
            "deferred_CPT_entries_for_targeted_external_review": 2,
        }
        (src / m.REPORT).write_text(json.dumps(report))
        yield src, dest


def test_private_report_correct_and_no_overwrite(private_workspace):
    src, dest = private_workspace
    old_csv = (src / m.CPT_QUEUE).read_bytes()
    report = m.prepare(src, dest)
    assert report["local_private_queue_entries"] == 2
    assert report["new_core_imaging_codes_added"] == 0
    assert report["patient_or_clinical_event_rows_read"] == 0
    assert report["clinical_codebook_approved"] is False
    assert report["full_clinical_scan_enabled"] is False
    assert report["step56_queue_SHA256"] == hashlib.sha256(old_csv).hexdigest()
    assert (src / m.CPT_QUEUE).read_bytes() == old_csv
    assert dest.stat().st_mode & 0o077 == 0
    assert (dest / m.DECISIONS).stat().st_mode & 0o077 == 0
    assert (dest / m.SUMMARY).stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        m.prepare(src, dest)


def test_untrusted_step56_report_blocks(private_workspace):
    src, dest = private_workspace
    bad = json.loads((src / m.REPORT).read_text())
    bad["clinical_codebook_approved"] = True
    (src / m.REPORT).write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="safe"):
        m.prepare(src, dest)
    assert not dest.exists()


def test_forged_reference_count_rejected(private_workspace):
    src, dest = private_workspace
    bad = json.loads((src / m.REPORT).read_text())
    bad["deferred_CPT_entries_for_targeted_external_review"] = 100
    (src / m.REPORT).write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="size"):
        m.prepare(src, dest)


def test_external_destination_is_rejected(private_workspace):
    src, _ = private_workspace
    with pytest.raises(ValueError, match="results/phase1"):
        m.prepare(src, Path("/tmp/step57_outside"))


def test_no_clinical_source_io_in_step57_module():
    from pathlib import Path
    p = Path(m.__file__).read_text()
    assert "zipfile.ZipFile(" not in p
    assert "sqlite3" not in p
    assert "data_use_approvals_changed" in p
