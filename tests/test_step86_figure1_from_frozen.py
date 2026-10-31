"""Synthetic-only validation for source-backed Figure 1 generation."""
from copy import deepcopy

import pytest

from scripts import step86_figure1_from_frozen as s86

def fake_aggregate():
    rows={}
    for p,den in enumerate(s86.EXPECTED_N):
        rows[f"P|{s86.COHORT}|P={p}"]={"n":den}
        for i,(mod,_) in enumerate(s86.MODALITIES):
            rows[f"MODALITY_P|{s86.COHORT}|P={p}|{mod}"]={
                "n":den,"imp":int(den*(.12+i*.03)),
                "new_day0_other":int(den*(.05+i*.02))}
    return {"stage":"STEP68_SINGLE_SCAN_CPT14_WINDOWS_AND_VERSIONED_SYSTEM_DISCOVERY_V2",
            "patient_cohort_aggregates":rows}

def test_generate_from_eligible_frozen_modality_counts(tmp_path):
    data=s86.get_data(fake_aggregate())
    assert len(data)==2
    assert len(data[0])==len(s86.MODALITIES)
    assert data[1][0]["index_pct"]<data[1][0]["same_day_pct"]
    p=tmp_path/"test_fig.png"
    s86.draw(data,p)
    assert p.exists() and p.stat().st_size>10000

def test_reconcile_against_supplement_table(tmp_path):
    from docx import Document
    data=s86.get_data(fake_aggregate())
    d=Document()
    tbl=d.add_table(rows=1,cols=4)
    for cell,value in zip(tbl.rows[0].cells,
                          ("Modality","I63 flag","Index inpatient (%)","Index or other same-day (%)")):
        cell.text=value
    for p in (0,1):
        for point in data[p]:
            row=tbl.add_row()
            for cell,value in zip(row.cells,(point["label"],f"P={p}",
                f'{point["index_pct"]:.2f}',f'{point["same_day_pct"]:.2f}')):
                cell.text=value
    output=tmp_path/"synthetic.docx"
    d.save(output)
    assert s86.verify_supplement(data,output)
    tbl.rows[1].cells[2].text="999.99"
    d.save(output)
    with pytest.raises(ValueError,match="disagree"):
        s86.verify_supplement(data,output)

def test_requires_complete_cohort_counts():
    x=fake_aggregate()
    x["patient_cohort_aggregates"][f"P|{s86.COHORT}|P=1"]["n"]-=1
    with pytest.raises(ValueError,match="denominator"):
        s86.get_data(x)

def test_rejects_nonbinomial_flags():
    x=fake_aggregate()
    key=f"MODALITY_P|{s86.COHORT}|P=0|CT_HEAD"
    x["patient_cohort_aggregates"][key]["new_day0_other"]=60000
    with pytest.raises(ValueError,match="Non-binomial"):
        s86.get_data(x)

def test_requires_frozen_source_policy():
    x=fake_aggregate()
    x["stage"]="UNVALIDATED"
    with pytest.raises(ValueError,match="frozen"):
        s86.get_data(x)
