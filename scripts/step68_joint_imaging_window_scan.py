#!/usr/bin/env python3
"""Step68: one checkpointed LOCAL-ONLY procedure pass, several scientific tests.

Only approved-source workstation use. Frozen Step62 indexed IMP CPT14
baseline, Step63 reciprocal-unique ED pairs, and deliberately looser
same-patient timing sensitivity. Exact non-CPT14 codes are private
DISCOVERY FREQUENCIES, never automatically called clinical imaging.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date, timedelta
import csv
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "results/phase1/full_reconstruction_private/step68_procedure_windows_private"
DB = "step68_procedure_windows_LOCAL_ONLY.sqlite"
REPORT = "step68_aggregate_LOCAL_ONLY.json"
POLICY = "STEP68_SINGLE_SCAN_CPT14_WINDOWS_AND_SYSTEM_DISCOVERY_V1"
ACK = s62.ACK
# One patient's same-day code may belong to a different provider/episode.
IMP, ED, ED_F, NONIMP_PRE2, NONIMP_DAY0, NONIMP_POST2 = (1,2,4,8,16,32)
ANY_PRE2, ANY_DAY0, ANY_POST2, NONIMP_PRE7, ANY_PRE7 = (64,128,256,512,1024)
ALL_BITS = (IMP,ED,ED_F,NONIMP_PRE2,NONIMP_DAY0,NONIMP_POST2,
            ANY_PRE2,ANY_DAY0,ANY_POST2,NONIMP_PRE7,ANY_PRE7)
SCOPE = ("INDEX_IMP","UNIQUE_ED","NONIMP_PRE2","NONIMP_DAY0","NONIMP_POST2")
SYSTEMS = frozenset(("CPT","HCPCS","SNOMED","ICD-10-PCS"))
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS progress(stage TEXT PRIMARY KEY,seen INTEGER NOT NULL,done INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS flags(cohort TEXT,patient TEXT,modality TEXT,mask INTEGER NOT NULL,
 PRIMARY KEY(cohort,patient,modality));
CREATE TABLE IF NOT EXISTS code_profile(system TEXT,code TEXT,scope TEXT,n INTEGER NOT NULL,
 PRIMARY KEY(system,code,scope));
CREATE TABLE IF NOT EXISTS system_profile(system TEXT,scope TEXT,n INTEGER NOT NULL,
 PRIMARY KEY(system,scope));
CREATE TABLE IF NOT EXISTS counters(name TEXT PRIMARY KEY,n INTEGER NOT NULL);
"""
def _iso(compact):
    return date(int(compact[:4]),int(compact[4:6]),int(compact[6:8]))

def _snapshot(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise ValueError("Frozen source SQLite database is missing or symlinked")
    st=p.stat()
    return {"bytes":st.st_size,"mtime_ns":st.st_mtime_ns,
            "path":str(p.resolve())}

def _verified(folder):
    if Path(folder).is_symlink():
        raise ValueError("Step68 private output may not be a symlink")
    return s62._private_dir(folder)

def _progress(db):
    row=db.execute("SELECT seen,done FROM progress WHERE stage='procedure'").fetchone()
    return row if row else (0,0)

def _subjects(db):
    """Cohort membership is copied to memory from Step63 read-only."""
    people=defaultdict(list)
    idx=db.execute("SELECT cohort,patient,encounter,start,end,principal FROM main.idx")
    for cohort,p,e,start,end,principal in idx:
        beginning=_iso(start)
        end_date=_iso(end)
        people[p].append({"cohort":cohort,"patient":p,"imp":e,
                          "start":start,"end":end,"date":beginning,
                          "start_date":beginning,"end_date":end_date,
                          "P":principal,"ed":None,"ed_start":None,
                          "ed_end":None,"ed_f":False})
    bypair={(ep["cohort"],ep["patient"]):ep for eps in people.values() for ep in eps}
    for cohort,p,ed,edstart,edend,edflag,ipflag in db.execute("""
        SELECT l.cohort,l.patient,l.ed,l.ed_start,l.ed_end,
               ev.end_derived,ip.start_derived
        FROM main.linked l
        JOIN main.evt ev ON ev.patient=l.patient AND ev.encounter=l.ed
        JOIN main.evt ip ON ip.patient=l.patient AND ip.encounter=l.imp"""):
        episode=bypair[(cohort,p)]
        episode["ed"]=ed
        episode["ed_start"]=edstart[:10].replace("-","")
        episode["ed_end"]=edend[:10].replace("-","")
        episode["ed_f"]=(edflag.strip().upper()=="F" and
                         ipflag.strip().upper()=="F")
    return people

def _flags(ep, encounter, day):
    """Return patient-level sensitivity mask; windows never relabel episodes."""
    mask=0
    if ep["imp"]==encounter and ep["start"] <= day <= ep["end"]:
        mask |= IMP
    if (ep["ed"] is not None and encounter==ep["ed"]
            and ep["ed_start"] <= day <= ep["ed_end"]):
        mask |= ED
        if ep["ed_f"]:
            mask |= ED_F
    d=_iso(day)
    diff=(d-ep["date"]).days
    if -2 <= diff <= -1:
        mask |= ANY_PRE2
        if encounter != ep["imp"]:
            mask |= NONIMP_PRE2
    if diff == 0:
        mask |= ANY_DAY0
        if encounter != ep["imp"]:
            mask |= NONIMP_DAY0
    if 1 <= diff <= 2:
        mask |= ANY_POST2
        if encounter != ep["imp"]:
            mask |= NONIMP_POST2
    if -7 <= diff <= -1:
        mask |= ANY_PRE7
        if encounter != ep["imp"]:
            mask |= NONIMP_PRE7
    return mask

def _scope(ep,encounter,day,mask):
    """Exact-code candidate frequency contexts, NOT verified imaging."""
    scopes=[]
    if mask & IMP:
        scopes.append("INDEX_IMP")
    if mask & ED:
        scopes.append("UNIQUE_ED")
    if mask & NONIMP_PRE2:
        scopes.append("NONIMP_PRE2")
    if mask & NONIMP_DAY0:
        scopes.append("NONIMP_DAY0")
    if mask & NONIMP_POST2:
        scopes.append("NONIMP_POST2")
    return scopes

def _batch(db,records,subjects):
    flags={}
    codes=Counter()
    systems=Counter()
    audit=Counter()
    for row in records:
        p=(row.get("patient_id") or "").strip()
        episodes=subjects.get(p)
        if not episodes:
            continue
        audit["rows_subject_patient"]+=1
        system=(row.get("code_system") or "").strip().upper()
        if system not in SYSTEMS:
            audit["rows_other_system"]+=1
            continue
        e=(row.get("encounter_id") or "").strip()
        day=s62.parsedate(row.get("date"))
        if not day or not e:
            audit["rows_missing_day_or_encounter"]+=1
            continue
        code=(row.get("code") or "").strip()
        if not code or len(code)>64:
            audit["rows_missing_or_oversized_code"]+=1
            continue
        for ep in episodes:
            mask=_flags(ep,e,day)
            if mask==0:
                continue
            audit["rows_in_any_window_cohort_memberships"]+=1
            modality=s62.CPT.get(code) if system=="CPT" else None
            if modality:
                key=(ep["cohort"],p,modality)
                flags[key]=flags.get(key,0)|mask
            for scope in _scope(ep,e,day,mask):
                systems[(system,scope)]+=1
                codes[(system,code,scope)]+=1
    if flags:
        db.executemany("""INSERT INTO flags VALUES(?,?,?,?)
          ON CONFLICT(cohort,patient,modality)
          DO UPDATE SET mask=(flags.mask | excluded.mask)""",
          ((*key,value) for key,value in flags.items()))
    if codes:
        db.executemany("""INSERT INTO code_profile VALUES(?,?,?,?)
          ON CONFLICT(system,code,scope)
          DO UPDATE SET n=n+excluded.n""",
          ((*key,n) for key,n in codes.items()))
    if systems:
        db.executemany("""INSERT INTO system_profile VALUES(?,?,?)
          ON CONFLICT(system,scope) DO UPDATE SET n=n+excluded.n""",
          ((*key,n) for key,n in systems.items()))
    if audit:
        db.executemany("""INSERT INTO counters VALUES(?,?)
          ON CONFLICT(name) DO UPDATE SET n=n+excluded.n""",
          audit.items())
    return audit

def _scan(db,archive,member,preflight,subjects,chunk=20000,stop_after=None):
    expected=preflight["relevant_manifest_counts"]["procedure.csv"]["row_count"]
    seen,done=_progress(db)
    if done:
        return seen
    if seen>expected:
        raise ValueError("Checkpoint exceeds source procedure count")
    with archive.open(member,"r") as raw, io.TextIOWrapper(
            raw,encoding="utf-8-sig",newline="") as txt:
        reader=csv.DictReader(txt)
        if reader.fieldnames!=preflight["files"]["procedure.csv"]["headers"]:
            raise ValueError("Procedure header differs from source preflight")
        for _ in range(seen):
            if next(reader,None) is None:
                raise ValueError("Procedure source shorter than checkpoint")
        while True:
            rows=[]
            for _ in range(chunk):
                r=next(reader,None)
                if r is None:
                    break
                if None in r or any(v is None for v in r.values()):
                    raise ValueError("Malformed procedure source record")
                rows.append(r)
            if not rows:
                break
            with db:
                _batch(db,rows,subjects)
                seen+=len(rows)
                db.execute("""INSERT INTO progress VALUES('procedure',?,0)
                   ON CONFLICT(stage) DO UPDATE SET seen=excluded.seen,done=0""",
                   (seen,))
            if seen % 10000000 < chunk:
                print("Source procedure rows processed:",seen,flush=True)
            if stop_after is not None and seen>=stop_after:
                return seen
    if seen!=expected:
        raise ValueError("Procedure source row count failed reconciliation")
    with db:
        db.execute("UPDATE progress SET done=1 WHERE stage='procedure'")
    return seen

def _presence(mask):
    return {name:bool(mask & bit) for name,bit in (
        ("imp",IMP),("ed",ED),("ed_f",ED_F),
        ("pre2",NONIMP_PRE2),("day0_other",NONIMP_DAY0),
        ("post2_other",NONIMP_POST2),("pre7",NONIMP_PRE7),
        ("any_pre2",ANY_PRE2),("any_day0",ANY_DAY0),
        ("any_post2",ANY_POST2))}

def _analyze(db,source):
    if _progress(db)[1]!=1:
        raise ValueError("Scan not yet complete; cannot summarize")
    # Patient-cohort grain. Six imaging modalities ORed into one indicator.
    patientflags=defaultdict(int)
    for cohort,p,mask in db.execute(
            "SELECT cohort,patient,mask FROM flags"):
        patientflags[(cohort,p)] |= mask
    rows=defaultdict(Counter)
    for cohort,p,start,principal in source.execute(
            "SELECT cohort,patient,start,principal FROM idx"):
        bit=patientflags.get((cohort,p),0)
        checks=_presence(bit)
        groups=(("COHORT",cohort),
                ("P",cohort+"|P="+str(principal)),
                ("YEAR",cohort+"|"+start[:4]),
                ("YEAR_P",cohort+"|"+start[:4]+"|P="+str(principal)))
        for key in groups:
            c=rows[key]
            c["n"]+=1
            for name,yes in checks.items():
                c[name]+=int(yes)
            if not checks["imp"]:
                for name in ("ed","ed_f","pre2","day0_other","pre7",
                             "any_pre2","any_day0"):
                    if checks[name]:
                        c["new_"+name]+=1
            if checks["imp"] and checks["ed"]:
                c["imp_and_ed"]+=1
    # Cross-check original same-IMP CPT14 baseline against Step62.
    for cohort in s62.COHORTS:
        baseline=source.execute("""SELECT COUNT(*) FROM idx i
           WHERE i.cohort=? AND EXISTS(
             SELECT 1 FROM image im
             WHERE im.cohort=i.cohort AND im.patient=i.patient)""",
             (cohort,)).fetchone()[0]
        if rows[("COHORT",cohort)]["imp"]!=baseline:
            raise ValueError("Recomputed baseline CPT14 differs from frozen Step62")
    # Linked ED code events must be a subset of the patient day windows,
    # but patient-relative windows are NOT a proven connected care episode.
    for k,v in rows.items():
        if v["ed_f"]>v["ed"] or v["new_ed_f"]>v["new_ed"]:
            raise AssertionError("Date-quality nesting invalid")
        if v["imp"]+v["new_ed"]>v["n"]:
            raise AssertionError("Patient-level capture exceeds denominator")
    return rows

def _output(db,source,folder):
    counts=_analyze(db,source)
    def serial():
        return {kind+"|"+name:dict(sorted(n.items()))
                for (kind,name),n in sorted(counts.items())
                if n["n"]>=11}
    summary={
        "stage":POLICY,
        "procedure_source_rows_read":_progress(db)[0],
        "patient_cohort_aggregates":serial(),
        "code_system_scope_rows_NOT_patients":list(db.execute(
            "SELECT system,scope,n FROM system_profile ORDER BY system,scope")),
        "matched_source_row_counters_NOT_patients":dict(db.execute(
            "SELECT name,n FROM counters")),
        "not_for_public_release_without_institutional_review":True,
        "discovery_code_frequencies_retained_IN_PRIVATE_SQLITE_ONLY":True,
        "P_0_includes_secondary_blank_unmarked":True,
        "ED_not_same_HCO_verified":True,
        "any_patient_window_not_same_episode_verified":True,
        "performed_imaging_verified":False,
    }
    outfile=folder/REPORT
    if outfile.exists():
        raise FileExistsError("Report already exists; will not overwrite")
    fd,tmp=tempfile.mkstemp(prefix=".step68_",dir=str(folder))
    try:
        with os.fdopen(fd,"w",encoding="utf8") as f:
            json.dump(summary,f,indent=2,sort_keys=True)
            f.write("\n")
        os.chmod(tmp,0o600)
        os.link(tmp,outfile)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return counts

def _print(counts):
    print("STEP68 SOURCE PROCEDURE CPT14; PATIENT/COHORT GRAIN; LOCAL ONLY")
    print("Counts do not represent confirmed imaging or same-hospital ED care.")
    print("P=0 includes missing/blank/secondary I63 indicators.")
    for kind in ("COHORT","P","YEAR","YEAR_P"):
        print("\nBY",kind)
        for (group,name),c in sorted(counts.items()):
            if group!=kind:
                continue
            if c["n"]<11:
                print("Suppressed group n<11")
                continue
            print(name,"n",c["n"],"IMP_CPT14",c["imp"],
                  "ED_new",c["new_ed"],"ED_F_new",c["new_ed_f"],
                  "nonIMP_pre2_new",c["new_pre2"],
                  "nonIMP_day0_new",c["new_day0_other"],
                  "nonIMP_pre7_new",c["new_pre7"],
                  "ANY_pre2_new",c["new_any_pre2"],
                  "ANY_day0_new",c["new_any_day0"])
    print("\nNot for public release without disclosure review.")

def run(zip_path,stage="all",folder=PRIVATE,chunk=20000,stop_after=None,
        preflight=s62.PREFLIGHT,step62=s62.DB,step63=s63.PRIVATE/s63.DATABASE):
    if stage not in ("scan","report","all"):
        raise ValueError("Stage is scan, report or all")
    if not 1<=chunk<=100000:
        raise ValueError("Chunk must be between 1 and 100000")
    folder=_verified(folder)
    with s62.single_writer(folder):
        p62=Path(step62);p63=Path(step63)
        snap62,snap63=_snapshot(p62),_snapshot(p63)
        main=sqlite3.connect("file:"+str(p63.resolve())+"?mode=ro",uri=True)
        try:
            main.execute("ATTACH DATABASE ? AS baseline",
                         ("file:"+str(p62.resolve())+"?mode=ro",))
            main.execute("PRAGMA query_only=ON")
            s64.verify(main,p62,p63)
            frozen=json.dumps({"policy":POLICY,"s62":snap62,"s63":snap63},
                              sort_keys=True)
            archive=None
            if stage in ("scan","all"):
                archive,members,prior,zipfinger=s62.verified_zip(zip_path,preflight)
                frozen=json.dumps({"policy":POLICY,"s62":snap62,
                                   "s63":snap63,"zip":zipfinger},sort_keys=True)
            if (folder/DB).is_symlink():
                raise ValueError("Step68 database cannot be symlinked")
            previous_umask=os.umask(0o077)
            try:
                db=sqlite3.connect(str(folder/DB))
            finally:
                os.umask(previous_umask)
            try:
                os.chmod(folder/DB,stat.S_IRUSR|stat.S_IWUSR)
                db.execute("PRAGMA journal_mode=DELETE")
                db.execute("PRAGMA synchronous=FULL")
                db.executescript(SCHEMA)
                old=db.execute("SELECT v FROM meta WHERE k='frozen'").fetchone()
                if old:
                    if stage in ("scan","all") and old[0]!=frozen:
                        raise ValueError("Step68 input snapshot changed; refusal")
                    if stage=="report":
                        meta=json.loads(old[0])
                        if any(meta.get(k)!=v for k,v in
                               (("policy",POLICY),("s62",snap62),("s63",snap63))):
                            raise ValueError("Step68 private snapshot changed")
                elif stage=="report":
                    raise ValueError("Scan has not been started")
                else:
                    db.execute("INSERT INTO meta VALUES('frozen',?)",(frozen,))
                    db.commit()
                if stage in ("scan","all") and not _progress(db)[1]:
                    seen=_scan(db,archive,members["procedure.csv"],prior,
                               _subjects(main),chunk,stop_after)
                    print("Step68 procedure checkpoint rows:",seen,
                          "complete:",bool(_progress(db)[1]),flush=True)
                if stage in ("report","all") and _progress(db)[1]:
                    report=folder/REPORT
                    with closing(sqlite3.connect(
                            "file:"+str(p62.resolve())+"?mode=ro",
                            uri=True)) as original:
                        original.execute("PRAGMA query_only=ON")
                        if not report.exists():
                            counts=_output(db,original,folder)
                        else:
                            counts=_analyze(db,original)
                    _print(counts)
                    print("PRIVATE aggregate report:",report)
                    print("PRIVATE discovery code frequencies:",folder/DB)
                return _progress(db)
            finally:
                db.close()
                if archive is not None:
                    archive.close()
        finally:
            main.close()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip",type=Path,required=True)
    p.add_argument("--stage",choices=("scan","report","all"),default="all")
    p.add_argument("--acknowledge",required=True)
    p.add_argument("--chunk",type=int,default=20000)
    args=p.parse_args()
    if args.acknowledge!=ACK:
        p.error("Approved existing clinical data processing attestation required")
    run(args.zip,args.stage,chunk=args.chunk)

if __name__=="__main__":
    main()
