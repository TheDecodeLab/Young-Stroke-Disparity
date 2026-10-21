"""Public-only fabricated CMS ZIP fixtures; fake code profiles, no clinical rows."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import sqlite3

import pytest

from scripts import step74_cms_pcs_codebook_review as s74


def cms_zip(lines,name="icd10pcs_codes_2024.txt"):
    b=BytesIO()
    with ZipFile(b,"w",ZIP_DEFLATED) as z:
        z.writestr(name,"\n".join(lines)+"\n")
    return b.getvalue()


def test_discover_realistic_links_and_same_FY_baseline_choice():
    html1="""<a href="/files/zip/2024-icd-10-pcs-codes-file.zip">
              2024 ICD-10-PCS Codes File (ZIP)</a>
       <a href="/files/zip/2025-icd-10-pcs-codes-file.zip">
              2025 ICD-10-PCS Codes File (ZIP)</a>"""
    html2="""<a href="/medicare/coding/2016-pcs-long-abbrev-titles.zip">
              2016 PCS Long and Abbreviated Titles (ZIP)</a>"""
    for yr in range(2017,2024):
        html2+='''<a href="/files/zip/%d-icd-10-pcs-codes-file.zip">
              %d ICD-10-PCS Codes File (ZIP)</a>'''%(yr,yr)
    found=s74.select_catalog(((s74.CMS_PAGES[0],html1),
                              (s74.CMS_PAGES[1],html2)))
    assert set(found)==set(range(2016,2026))
    assert found[2024][0].startswith("https://www.cms.gov/")
    assert "Long and Abbreviated" in found[2016][1]
    with pytest.raises(ValueError,match="missing for FY"):
        s74.select_catalog(((s74.CMS_PAGES[0],html1),))


def test_public_zip_parser_and_clinical_candidate_conservatism():
    z=cms_zip([
      "B020ZZZ Computerized Tomography of Brain",
      "B030ZZZ Magnetic Resonance Imaging of Brain",
      "B321ZZZ Computerized Tomography of Carotid Arteries",
      "B331ZZZ Magnetic Resonance Imaging of Carotid Arteries",
      "B240ZZZ Ultrasonography of Heart",
      "B310ZZZ Fluoroscopy of Right Upper Arm Artery",
      "0JH60BZ Insertion of Device into Soft Tissue",
    ])
    titles=s74.parse_titles(z,minimum=3)
    assert len(titles)==6
    assert s74.candidate("B020ZZZ",titles["B020ZZZ"])=="REVIEW_CNS_CT"
    assert s74.candidate("B030ZZZ",titles["B030ZZZ"])=="REVIEW_CNS_MR"
    assert s74.candidate("B321ZZZ",titles["B321ZZZ"])=="REVIEW_UPPER_ARTERIAL_CT"
    assert s74.candidate("B331ZZZ",titles["B331ZZZ"])=="REVIEW_UPPER_ARTERIAL_MR"
    assert s74.candidate("B240ZZZ",titles["B240ZZZ"]) is None
    assert s74.candidate("B310ZZZ",titles["B310ZZZ"]) is None
    assert s74.candidate("B320ZZZ","CT of Left Femur") is None
    assert s74.candidate("B020","CT brain") is None
    with pytest.raises(ValueError,match="Insufficient"):
        s74.parse_titles(z,minimum=200)


def test_legacy_order_titles_and_public_download_cache(tmp_path):
    z=cms_zip([
        "00001 B020ZZZ 1 CT Brain Computerized Tomography of Brain",
        "00002 B030ZZZ 1 MR Brain Magnetic Resonance Imaging of Brain",
    ],"icd10pcs_long_titles_2016.txt")
    assert "B020ZZZ" in s74.parse_titles(z,minimum=2)
    url="https://www.cms.gov/files/zip/2024-pcs-codes.zip"
    data,sha=s74.download_public(url,tmp_path,2024,downloader=lambda u:z)
    assert data==z and len(sha)==64
    second,sha2=s74.download_public(url,tmp_path,2024,
                                  downloader=lambda u: (_ for _ in ()).throw(
                                      AssertionError("cached file was re-fetched")))
    assert second==data and sha==sha2
    with pytest.raises(ValueError,match="official cms.gov"):
        s74.download_public("https://example.org/fake.zip",tmp_path,2024,
                            downloader=lambda u:z)
    with pytest.raises(ValueError,match="bounded ZIP"):
        s74.download_public(url,tmp_path,2025,downloader=lambda u:b"not a zip")


def test_exact_source_code_coverage_is_rows_not_patients():
    db=sqlite3.connect(":memory:")
    db.execute("""ATTACH DATABASE ':memory:' AS capture""")
    db.execute("""CREATE TABLE capture.code_profile(
      system TEXT,code TEXT,scope TEXT,service_year TEXT,P INTEGER,n INTEGER)""")
    db.executemany("INSERT INTO capture.code_profile VALUES(?,?,?,?,?,?)",[
        ("ICD-10-PCS","B020ZZZ","INDEX_IMP","2020",1,7),
        ("ICD-10-PCS","B030ZZZ","NONIMP_DAY0","2020",1,15),
        ("ICD-10-PCS","B240ZZZ","INDEX_IMP","2020",0,30),
        ("ICD-10-PCS","B020ZZZ","UNIQUE_ED","2020",0,2),
        ("ICD-10-PCS","B999ZZZ","INDEX_IMP","2020",0,11),
        ("CPT","70450","INDEX_IMP","2020",1,100),
        ("ICD-10-PCS","B020ZZZ","INDEX_IMP","2019",1,4),
    ])
    titles={2020:{"B020ZZZ":"Computerized Tomography of Brain",
                  "B030ZZZ":"Magnetic Resonance Imaging of Brain",
                  "B240ZZZ":"Ultrasonography of Heart"},
            2021:{"B020ZZZ":"Computerized Tomography of Brain",
                  "B030ZZZ":"Magnetic Resonance Imaging of Brain"}}
    totals,private=s74.crosswalk(db,titles)
    assert totals[("2020",1,"INDEX_IMP")]["source_rows"]==7
    assert totals[("2020",1,"INDEX_IMP")][
        "REVIEW_ONLY_potential_neuroimaging_source_rows"]==7
    assert totals[("2020",1,"NONIMP_DAY0")][
        "REVIEW_ONLY_potential_neuroimaging_source_rows"]==15
    assert totals[("2020",0,"INDEX_IMP")][
        "REVIEW_ONLY_potential_neuroimaging_source_rows"]==0
    assert totals[("2020",0,"INDEX_IMP")][
        "not_in_two_FY_catalogs_rows"]==11
    assert len([r for r in private if r["service_year"]=="2020"])==3
    assert all("source_rows_cohort_memberships" in x for x in private)
    assert all("patient" not in x for x in private)
    db.close()
