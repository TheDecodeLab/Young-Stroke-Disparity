"""Step56 all-synthetic reference coverage tests; no clinical records."""
import csv
import hashlib
import io
import json
import tempfile

import pytest

from scripts import step56_reference_vocabulary_coverage_triage as m


def synthetic_inputs():
    originals=[]
    disposed=[]
    situations=[
        ("CPT","70551","core_exact_CPT_modality_candidate","MRI_BRAIN"),
        ("CPT","77777","defer_CPT_not_in_literature_core","MRI_BRAIN"),
        ("SNOMED","111000","defer_unmapped_or_unverified_system","CTA_HEAD"),
        ("HCPCS","G1111","defer_unmapped_or_unverified_system","MRA_NECK"),
    ]
    for n,(system,code,status,category) in enumerate(situations,1):
        refid=f"{n:064x}"
        originals.append({
            **{key:"" for key in m.REVIEW_COLS},
            "review_id":refid,
            "code_system":system,
            "code":code,
            "reference_description":("MRI brain" if system=="CPT" else "reference text"),
            "automated_candidate_NOT_APPROVED":category,
        })
        disposed.append({
            **{key:"" for key in m.COLS},
            "review_id":refid,
            "code_system":system,
            "code":code,
            "literature_status":status,
        })
    status_counts={
        "core_exact_CPT_modality_candidate":1,
        "defer_CPT_not_in_literature_core":1,
        "defer_unmapped_or_unverified_system":2,
    }
    metadata={"reference_rows_examined":len(originals),
              "literature_status_counts":status_counts}
    return originals,disposed,metadata


def make_csv(rows, fields):
    out=io.StringIO(newline="")
    writer=csv.DictWriter(out,fieldnames=fields,lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


@pytest.fixture
def local_workspace():
    m.DEST.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="step56_synthetic_",dir=m.DEST.parent) as folder:
        root=m.Path(folder)
        step46=root/"original_reference"
        step55=root/"literature_dispositions"
        result=root/"coverage_results"
        step46.mkdir(mode=0o700)
        step55.mkdir(mode=0o700)
        originals,disposed,meta=synthetic_inputs()
        src_csv=make_csv(originals,m.REVIEW_COLS)
        step46_status={
            "stage":"STEP46_PRIVATE_IMAGING_REVIEW_PREPARED",
            "clinical_event_rows_read":0,
            "codebook_clinically_validated":False,
            "full_reference_candidate_entries_preserved":len(originals),
        }
        source_status=json.dumps(step46_status).encode()
        (step46/m.STATUS).write_bytes(source_status)
        (step46/m.INVENTORY).write_bytes(src_csv)
        meta.update({
            "stage":"STEP55_LITERATURE_BASED_TERMINOLOGY_ADJUDICATION_ONLY",
            "clinical_event_rows_read":0,
            "codebook_signed_off":False,
            "full_clinical_scan_performed":False,
            "source_step46_status_sha256":hashlib.sha256(source_status).hexdigest(),
            "source_step46_inventory_sha256":hashlib.sha256(src_csv).hexdigest(),
        })
        (step55/m.SUMMARY).write_text(json.dumps(meta))
        (step55/m.DISPOSITIONS).write_bytes(make_csv(disposed,m.COLS))
        yield step46,step55,result


def test_aggregate_breakdown_is_reference_rows_not_procedure_frequencies():
    original,classified,status=synthetic_inputs()
    summary,queue=m.analyze(original,classified,status)
    assert summary["reference_entries_reconciled"]==4
    assert summary["reference_counts_by_code_system"]=={
        "CPT":2,"HCPCS":1,"SNOMED":1,
    }
    assert summary["deferred_CPT_entries_for_targeted_external_review"]==1
    assert summary["unmapped_code_systems_recorded_in_actual_procedure_events"]=="UNKNOWN"
    assert summary["reference_terminology_counts_are_NOT_procedure_use_frequencies"] is True
    assert summary["clinical_codebook_approved"] is False
    assert summary["full_clinical_scan_enabled"] is False
    assert queue[0]["code"]=="77777"
    assert queue[0]["verified_external_coding_meaning_PENDING"]=="PENDING"


def test_provenance_failure_duplicate_identity_is_blocked():
    originals,classified,meta=synthetic_inputs()
    classified[1]["review_id"]=classified[0]["review_id"]
    with pytest.raises(ValueError,match="Duplicate|duplicate"):
        m.analyze(originals,classified,meta)


def test_misclassified_code_fails_closed():
    originals,classified,meta=synthetic_inputs()
    classified[0]["code"]="00000"
    with pytest.raises(ValueError,match="differs"):
        m.analyze(originals,classified,meta)


def test_status_counts_must_reconcile():
    originals,classified,meta=synthetic_inputs()
    meta["literature_status_counts"]["core_exact_CPT_modality_candidate"]=2
    with pytest.raises(ValueError,match="reconcile"):
        m.analyze(originals,classified,meta)


def test_private_output_restricts_permissions_and_refuses_overwrite(local_workspace):
    step46,step55,output=local_workspace
    summary=m.prepare(step46,step55,output)
    assert summary["reference_entries_reconciled"]==4
    assert output.stat().st_mode & 0o077==0
    assert (output/m.REPORT).stat().st_mode & 0o077==0
    assert (output/m.CPT_QUEUE).stat().st_mode & 0o077==0
    assert (output/m.REPORT).is_file()
    assert "reference text" not in (output/m.REPORT).read_text()
    before=(output/m.CPT_QUEUE).read_bytes()
    with pytest.raises(FileExistsError):
        m.prepare(step46,step55,output)
    assert (output/m.CPT_QUEUE).read_bytes()==before


def test_source_reference_change_after_step55_prevents_triage(local_workspace):
    step46,step55,output=local_workspace
    with (step46/m.INVENTORY).open("a") as dest:
        dest.write("UNREVIEWED_TAMPERING")
    with pytest.raises(ValueError,match="provenance"):
        m.prepare(step46,step55,output)
    assert not output.exists()


def test_literature_status_signed_off_cannot_be_used_as_unapproved_inputs(local_workspace):
    step46,step55,output=local_workspace
    report_path=step55/m.SUMMARY
    report=json.loads(report_path.read_text())
    report["codebook_signed_off"]=True
    report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match="provenance"):
        m.prepare(step46,step55,output)


def test_bad_or_outside_output_path_rejected(local_workspace):
    step46,step55,_=local_workspace
    with pytest.raises(ValueError,match="results/phase1"):
        m.prepare(step46,step55,m.Path("/tmp/step56_external"))
