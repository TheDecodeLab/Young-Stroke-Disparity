"""Step63 uses only fabricated CSV rows; no research-data fixtures."""
import csv
import io
import json
import sqlite3
import stat
import zipfile

import pytest

from scripts import step62_checkpointed_cohort as s62
from scripts import step63_ed_encounter_feasibility as s63


@pytest.fixture
def fake(tmp_path, monkeypatch):
    monkeypatch.setattr(s62, "ROOT", tmp_path)
    root = tmp_path / "results/phase1/full_reconstruction_private"
    old = root / "s62_synthetic"
    new = root / "s63_synthetic"
    pre = tmp_path / "step36_SYNTH.json"
    z = tmp_path / "SYNTH_ONLY.zip"

    enc = [
        ["A","AIP","20200105","20200106","IMP"],
        ["A","AED","20200104","20200104","EMER"],
        ["B","BIP","20200109","20200110","IMP"],
        ["B","BED","20200108","20200108","EMER"],
        # This non-stroke-coded IMP still competes for B's ED.
        ["B","BOTHER","20200109","20200110","IMP"],
        ["C","CIP","20200107","20200108","IMP"],
        # Two EDs compete for one index IMP.
        ["C","CED1","20200106","20200106","EMER"],
        ["C","CED2","20200106","20200106","EMER"],
        ["D","DIP","20200112","20200113","IMP"],
        # Date-discordant ED entries must remain quarantined.
        ["D","DED","20200111","20200111","EMER"],
        ["D","DED","20200110","20200110","EMER"],
        ["E","EIP","20160101","20160103","IMP"],
        ["E","EED","20151231","20151231","EMER"],
    ]
    files = {
        "encounter": (
            ["patient_id","encounter_id","start_date","end_date","type"],
            enc),
        "diagnosis": (
            ["patient_id","encounter_id","code_system","code","date",
             "principal_diagnosis_indicator"],
            [[p,p+"IP","ICD-10-CM","I63.9",
              "20160101" if p=="E" else {"A":"20200105","B":"20200109",
              "C":"20200107","D":"20200112"}[p],"P"]
             for p in ("A","B","C","D","E")]),
        "patient": (
            ["patient_id","year_of_birth","sex","race","ethnicity"],
            [[p,"1980" if p=="E" else "1990","F","R","E"]
             for p in ("A","B","C","D","E")]),
        "procedure": (
            ["patient_id","encounter_id","date","code_system","code"],
            [["A","AIP","20200105","CPT","70551"]]),
    }
    details, manifest = {}, {}
    with zipfile.ZipFile(z, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for stage, (header, rows) in files.items():
            buf = io.StringIO(newline="")
            writer = csv.writer(buf)
            writer.writerow(header)
            writer.writerows(rows)
            body = buf.getvalue().encode()
            archive.writestr("synthetic/" + stage + ".csv", body)
            details[stage + ".csv"] = {
                "present": True, "headers": header,
                "uncompressed_bytes": len(body)}
            manifest[stage + ".csv"] = {"row_count": len(rows)}
    pre.write_text(json.dumps({
        "stage": "STEP36_RESEARCH_METADATA_PREFLIGHT",
        "clinical_rows_read": 0,
        "full_clinical_tables_scanned": False,
        "files": details,
        "relevant_manifest_counts": manifest
    }))
    for stage in s62.STAGES:
        assert s62.run(z, stage, preflight=pre,
                       folder=old, chunk=2)["complete"]
    return z, pre, old, new, len(enc)


def test_unique_ed_links_reject_both_kinds_of_competition(fake):
    z, pre, old, new, total = fake
    first = s63.run(z,"encounter",preflight=pre,step62_folder=old,
                    folder=new,chunk=3)
    assert first["complete"] and first["processed_rows"] == total
    assert first["quarantined_keys_LOCAL_ONLY"] == 1
    second = s63.run(z,"link",preflight=pre,step62_folder=old,folder=new)
    assert second["complete"] and second["processed_rows"] == 0
    with sqlite3.connect(str(new/s63.DATABASE)) as db:
        assert db.execute("SELECT COUNT(*) FROM pair").fetchone()[0] == 6
        assert db.execute("SELECT COUNT(*) FROM linked").fetchone()[0] == 4
        linked = set(db.execute("SELECT DISTINCT patient FROM linked"))
        assert linked == {("A",),("E",)}
        assert db.execute("SELECT COUNT(*) FROM evt WHERE kind='EMER'").fetchone()[0] == 5
        assert db.execute("SELECT COUNT(*) FROM ambiguous").fetchone()[0] == 1
        assert s63._progress(db,"encounter") == (total,1)
    report = json.loads((new/s63.REPORT).read_text())
    assert report["ED_procedure_scanned"] is False
    assert report["same_HCO_verified"] is False
    assert report["source_id_as_HCO"] is False
    assert report["unique_candidate_pair_rows"] == 6
    for cohort in s62.COHORTS:
        assert report["indexed_cohorts"][cohort][
            "uniquely_linked_ED_patients_date_only"] == 2
    assert "AED" not in json.dumps(report)
    assert stat.S_IMODE((new/s63.DATABASE).stat().st_mode) == 0o600
    assert stat.S_IMODE((new/s63.REPORT).stat().st_mode) == 0o600


def test_resume_checkpoint_without_repeating_rows(fake):
    z, pre, old, new, total = fake
    initial = s63.run(z,"encounter",preflight=pre,
                      step62_folder=old,folder=new,chunk=2,stop_after=2)
    assert not initial["complete"] and initial["processed_rows"] == 2
    restored = s63.run(z,"encounter",preflight=pre,
                       step62_folder=old,folder=new,chunk=3)
    assert restored["complete"] and restored["processed_rows"] == total
    assert restored["quarantined_keys_LOCAL_ONLY"] == 1
    with pytest.raises(ValueError,match="already completed"):
        s63.run(z,"encounter",preflight=pre,step62_folder=old,folder=new)


def test_cannot_link_before_completed_encounter_scan(fake):
    z, pre, old, new, _ = fake
    with pytest.raises(ValueError,match="prior stage"):
        s63.run(z,"link",preflight=pre,step62_folder=old,folder=new)
    assert s63.run(z,"encounter",preflight=pre,
                   step62_folder=old,folder=new)["complete"]


def test_blocks_source_drift_and_unapproved_output(fake, tmp_path):
    z, pre, old, new, _ = fake
    assert s63.run(z,"encounter",preflight=pre,
                   step62_folder=old,folder=new,chunk=2,stop_after=2)
    data = json.loads(pre.read_text())
    data["metadata_changed"] = True
    pre.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="fingerprint changed"):
        s63.run(z,"encounter",preflight=pre,step62_folder=old,folder=new)
    with pytest.raises(ValueError,match="gitignored private results"):
        s63.run(z,"encounter",preflight=pre,
                step62_folder=old,folder=tmp_path/"OUTSIDE")


def test_rejects_bad_ack_and_date_parsing():
    assert s63._iso("2020-01-02") == "2020-01-02"
    assert s63._iso("20200102") == "2020-01-02"
    assert s63._iso("20200230") is None
    with pytest.raises(SystemExit):
        s63.main(["--zip","unapproved.zip","--stage","encounter",
                  "--acknowledge","WRONG"])


def test_index_span_mismatch_blocks_all_linking(fake):
    z, pre, old, new, _ = fake
    assert s63.run(z,"encounter",preflight=pre,step62_folder=old,
                   folder=new)["complete"]
    # Artificially introduce inconsistent Step63 index snapshot.
    with sqlite3.connect(str(new/s63.DATABASE)) as db:
        db.execute("UPDATE idx SET start='20200102' WHERE patient='A'")
    with pytest.raises(ValueError,match="missing/conflicting IMP spans"):
        s63.run(z,"link",preflight=pre,step62_folder=old,folder=new)
    with sqlite3.connect(str(new/s63.DATABASE)) as db:
        assert db.execute("SELECT COUNT(*) FROM pair").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM linked").fetchone()[0] == 0
        assert s63._progress(db,"link") == (0,0)
