#!/usr/bin/env python3
"""Step74: official CMS PCS code-title discovery, source coverage and quasi CI.

No raw TriNetX source ZIP reread. No user patient/encounter identifiers or
individual records printed/saved. CMS candidates are NOT approved imaging.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import hashlib
import json
import math
import os
import re
import tempfile
import zipfile

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
    from scripts import step68_joint_imaging_window_scan as s68
    from scripts import step72_exploratory_demographic_models as s72
    from scripts import step73_uncertainty_support_diagnostics as s73
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64
    import step68_joint_imaging_window_scan as s68
    import step72_exploratory_demographic_models as s72
    import step73_uncertainty_support_diagnostics as s73
import sqlite3

CMS_PAGES=(
 "https://www.cms.gov/medicare/coding-billing/icd-10-codes",
 "https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-10-cm-icd-10-pcs-gem-archive",
)
FY=tuple(range(2016,2026))
PRIVATE=s62.ROOT/"results/phase1/full_reconstruction_private/step74_public_cms_private"
REPORT="step74_cms_pcs_crosswalk_LOCAL_ONLY.json"
SCOPES=("INDEX_IMP","NONIMP_DAY0","UNIQUE_ED")
SELECTED=("B02","B03","B32","B33")
REVIEW_TERMS=re.compile(
 r"\b(brain|cerebral|intracranial|carotid|vertebral|head|neck)\b",
 re.IGNORECASE)
CODE_LINE=re.compile(r"^\s*(?:[0-9]{5}\s+)?([A-Z0-9]{7})\s+(?:[01]\s+)?(.+)$")


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.open_href=None
        self.words=[]
        self.items=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.open_href=dict(attrs).get("href")
            self.words=[]
    def handle_data(self,text):
        if self.open_href is not None:
            self.words.append(text)
    def handle_endtag(self,tag):
        if tag=="a" and self.open_href is not None:
            self.items.append((self.open_href," ".join(self.words)))
            self.open_href=None
            self.words=[]


def valid_cms(url):
    x=urlparse(url)
    return (x.scheme=="https" and x.hostname=="www.cms.gov"
            and x.path.lower().endswith(".zip") and not x.username)


def select_catalog(pages):
    """Choose one official FY baseline code file per year, no fuzzy titles.

    FY2016 has a differently named long-title source.
    FY2024/2025 have in-year updates; choosing one baseline version is a
    discovery screen, not exact date-effective clinical classification.
    """
    files={}
    for page_url,html in pages:
        parser=Anchors()
        parser.feed(html)
        for href,title in parser.items:
            t=" ".join(title.split())
            m=re.match(r"^(20(?:1[6-9]|2[0-5]))\s+",t)
            if not m:
                continue
            year=int(m.group(1))
            correct=(("ICD-10-PCS Codes File" in t) if year!=2016 else
                     ("PCS Long and Abbreviated Titles" in t))
            if not correct or "(ZIP)" not in t:
                continue
            uri=urljoin(page_url,href)
            if valid_cms(uri) and year not in files:
                files[year]=(uri,t)
    missing=set(FY)-set(files)
    if missing:
        raise ValueError("CMS official PCS ZIP links missing for FY: "+
                         ",".join(map(str,sorted(missing))))
    return files


def download_public(url, folder, year, downloader=None):
    if not valid_cms(url):
        raise ValueError("Only official cms.gov HTTPS ZIP links allowed")
    name="cms_pcs_FY"+str(year)+".zip"
    target=folder/name
    if target.is_symlink():
        raise ValueError("CMS cache file must not be a symlink")
    if not target.exists():
        if downloader is None:
            def downloader(u):
                req=Request(u,headers={"User-Agent":"YoungStrokeResearchCodeReview/1.0"})
                with urlopen(req,timeout=90) as r:
                    if urlparse(r.geturl()).hostname!="www.cms.gov":
                        raise ValueError("CMS redirect left cms.gov host")
                    raw=r.read(60000001)
                return raw
        body=downloader(url)
        if len(body)>60000000 or not body.startswith(b"PK\x03\x04"):
            raise ValueError("CMS URL did not return a bounded ZIP archive")
        fd,tmp=tempfile.mkstemp(prefix=".cmspcs_",dir=folder)
        try:
            with os.fdopen(fd,"wb") as fh:
                fh.write(body)
            os.chmod(tmp,0o600)
            os.link(tmp,target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    content=target.read_bytes()
    if len(content)>60000000 or not zipfile.is_zipfile(BytesIO(content)):
        raise ValueError("Cached CMS ZIP is invalid")
    return content,hashlib.sha256(content).hexdigest()


def parse_titles(data,minimum=50):
    """Parse CMS fixed/text codes-title files; require B-prefix section data.

    Prefer the text member with the largest number of B-prefix code rows.
    Skip directories/giant members/metadata. CMS code titles are PUBLIC.
    """
    best={}
    with zipfile.ZipFile(BytesIO(data)) as z:
        for member in z.infolist():
            fname=member.filename.lower()
            if (member.is_dir() or not fname.endswith(".txt")
                or member.file_size>30000000):
                continue
            if not any(x in fname for x in ("code","title","order","pcs")):
                continue
            d={}
            raw=z.read(member).decode("latin-1")
            for ln in raw.splitlines():
                m=CODE_LINE.match(ln.strip())
                if not m:
                    continue
                code=m.group(1)
                if not code.startswith("B"):
                    continue
                title=" ".join(m.group(2).split())
                if len(title)<9:
                    continue
                if code in d and d[code]!=title:
                    raise ValueError("Conflicting official CMS code titles")
                d[code]=title
            if len(d)>len(best):
                best=d
    if len(best)<minimum:
        raise ValueError("Insufficient valid B-section titles in CMS ZIP")
    return best


def candidate(code,title):
    """Conservative REVIEW ONLY: imaging family and body-part text both required."""
    if len(code)!=7 or code[:3] not in SELECTED:
        return None
    if not REVIEW_TERMS.search(title):
        return None
    if code.startswith("B02"):
        return "REVIEW_CNS_CT"
    if code.startswith("B03"):
        return "REVIEW_CNS_MR"
    if code.startswith("B32"):
        return "REVIEW_UPPER_ARTERIAL_CT"
    if code.startswith("B33"):
        return "REVIEW_UPPER_ARTERIAL_MR"
    return None


def crosswalk(db,titles):
    """Rows are code-profile SOURCE ROW COUNTS, not distinct patients.

    Step68 profile has only service calendar year, not exact discharge
    date. FY calendar-year or FY+1 match is *approximate availability*.
    """
    stats=defaultdict(Counter)
    detail=[]
    for code,scope,yr,P,n in db.execute("""
        SELECT code,scope,service_year,P,SUM(n)
        FROM capture.code_profile
        WHERE system='ICD-10-PCS'
        GROUP BY code,scope,service_year,P
    """):
        if scope not in SCOPES or not (2016<=int(yr)<=2024):
            continue
        if P not in (0,1) or n<0 or len(code)>64:
            raise ValueError("Malformed frozen Step68 code profile")
        key=(str(yr),int(P),scope)
        c=stats[key]
        n=int(n)
        c["source_rows"]+=n
        fy_valid=tuple(titles[y][code] for y in (int(yr),int(yr)+1)
                       if code in titles.get(y,{}))
        if not fy_valid:
            c["not_in_two_FY_catalogs_rows"]+=n
            continue
        c["in_at_least_one_neighbor_FY_rows"]+=n
        review=sorted(set(filter(None,(candidate(code,ti) for ti in fy_valid))))
        if review:
            c["REVIEW_ONLY_potential_neuroimaging_source_rows"]+=n
            for tag in review:
                c[tag+"_rows"]+=n
            # Private-only per exact source code, for later approved review.
            detail.append({"service_year":str(yr),"P":int(P),"scope":scope,
                 "code":code,"source_rows_cohort_memberships":n,
                 "FY_codes_available":list(y for y in (int(yr),int(yr)+1)
                                            if code in titles.get(y,{})),
                 "FY_titles":list(fy_valid),"review_tags":review})
    return stats,detail


def quasi_check(table):
    """Approximate extra-binomial sensitivity, NOT HCO cluster correction."""
    print("\nQUASI-BINOMIAL INFLATION CHECK, NOT HOSPITAL ADJUSTMENT")
    for outcome in ("imp_any","same_day_any"):
        fit,x=s73.fit(table,s72.PRIMARY,outcome,"quality")
        ratio=float(fit.deviance/fit.df_resid)
        factor=math.sqrt(max(1.,ratio))
        print("outcome",outcome,"deviance_df","%.2f"%ratio,
              "nominal_interval_halfwidth_multiplier","%.2f"%factor)
        for field,ref,target in s73.TARGETS:
            r=s73.contrast(fit,x,field,ref,target)
            if r["n_target"]<11:
                continue
            margin=1.959963984540054*factor*r["nominal_SE_pp"]
            print(field,target,"vs",ref,
                  "RD_pp","%+.2f"%r["difference_pp"],
                  "INFLATED_95_INTERVAL_NOT_HCO",
                  "[%+.2f,%+.2f]"%(r["difference_pp"]-margin,
                                   r["difference_pp"]+margin))
    print("This is a diagnostic only; residual overdispersion does NOT solve HCO correlation.")


def fetch_catalog(cache):
    html=[]
    for url in CMS_PAGES:
        req=Request(url,headers={"User-Agent":"YoungStrokeResearchCodeReview/1.0"})
        with urlopen(req,timeout=60) as response:
            if urlparse(response.geturl()).hostname!="www.cms.gov":
                raise ValueError("CMS page redirected off official host")
            raw=response.read(4000000)
        html.append((url,raw.decode("utf-8",errors="replace")))
    chosen=select_catalog(html)
    titles={}
    hashes={}
    for year in FY:
        data,digest=download_public(chosen[year][0],cache,year)
        titles[year]=parse_titles(data)
        hashes[str(year)]={"url":chosen[year][0],"sha256":digest,
                           "section_B_code_titles":len(titles[year])}
        print("CMS FY",year,"official section-B code titles",len(titles[year]),
              flush=True)
    return titles,hashes


def main():
    files=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    if any(p.is_symlink() or not p.is_file() for p in files):
        raise FileNotFoundError("Frozen private SQLite checkpoints required")
    p62,p63,p68=(p.resolve() for p in files)
    priorfile=s68.PRIVATE/s68.REPORT
    if priorfile.is_symlink() or not priorfile.is_file():
        raise FileNotFoundError("Frozen Step68 aggregate report missing")
    prior=json.loads(priorfile.read_text(encoding="utf8"))
    if prior.get("stage")!=s68.POLICY:
        raise ValueError("Step68 policy does not match")
    # Model diagnostic is independent of CMS availability.
    with sqlite3.connect("file:"+str(p63)+"?mode=ro",uri=True) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:"+str(p62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",
                   ("file:"+str(p68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,p62,p63)
        frozen=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if frozen is None:
            raise ValueError("Step68 input signature unavailable")
        meta=json.loads(frozen[0])
        if (meta.get("policy")!=s68.POLICY or
            meta.get("s62")!=s68._snapshot(p62) or
            meta.get("s63")!=s68._snapshot(p63)):
            raise ValueError("Step68 private source signature mismatch")
        scan=db.execute("SELECT seen,done FROM capture.progress WHERE stage='procedure'").fetchone()
        if scan!=(993025015,1):
            raise ValueError("Step68 procedure scan not completed")
        table=s72.build(db)
        s72.verify(table,prior)
        quasi_check(table)
        folder=s62._private_dir(PRIVATE)
        print("\nFetching OFFICIAL PUBLIC CMS PCS titles FY2016-FY2025",flush=True)
        try:
            catalog,meta_catalog=fetch_catalog(folder)
        except (OSError,ValueError,zipfile.BadZipFile) as ex:
            print("CMS PUBLIC DOWNLOAD/FORMAT BLOCKER:",
                  type(ex).__name__,str(ex)[:200],flush=True)
            print("No source data modified. Need CMS archive access or a parser repair.")
            return 2
        summary,details=crosswalk(db,catalog)
        print("\nSTEP74 PCS CODE DISCOVERY: *source rows* (cohort memberships)")
        print("NOT patient counts. NO codes automatically added to imaging endpoint.")
        for key,c in sorted(summary.items()):
            year,P,scope=key
            if c["source_rows"]<11:
                print("source group suppressed (<11)")
                continue
            print("service_year",year,"P",P,"scope",scope,
                  "all_PCS_source_rows",c["source_rows"],
                  "valid_neighbor_FY_rows",c["in_at_least_one_neighbor_FY_rows"],
                  "REVIEW_ONLY_neuro_source_rows",
                    c["REVIEW_ONLY_potential_neuroimaging_source_rows"])
        out={"policy":"STEP74_DISCOVERY_ONLY_V1",
             "official_catalog_fy_metadata":meta_catalog,
             "public_codes_plus_private_source_frequencies_LOCAL_ONLY":details,
             "source_row_aggregates_LOCAL_ONLY":{
                   "|".join(map(str,k)):dict(v) for k,v in summary.items()},
             "service_year_not_discharge_date_caveat":True,
             "candidate_not_verified_performed_imaging":True,
             "not_patient_level_capture":True}
        path=folder/REPORT
        if path.exists() or path.is_symlink():
            raise FileExistsError("Existing Step74 report: no overwrite allowed")
        fd,tmp=tempfile.mkstemp(prefix=".step74_",dir=str(folder))
        try:
            with os.fdopen(fd,"w",encoding="utf8") as f:
                json.dump(out,f,indent=2,sort_keys=True)
                f.write("\n")
            os.chmod(tmp,0o600)
            os.link(tmp,path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        print("\nPRIVATE Step74 source-code review report:",path)
        print("HANDOFF: terminal output ONLY. No ZIP or private results upload.")
        return 0


if __name__=="__main__":
    raise SystemExit(main())
