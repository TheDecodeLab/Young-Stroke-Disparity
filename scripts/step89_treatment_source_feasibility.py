#!/usr/bin/env python3
"""Step89: bounded source metadata and frozen treatment-code feasibility check.

Never reads clinical CSV bodies, medication rows, patient identifiers, or original
procedure rows. Checks source member names/headers and an existing private
aggregate of code/source rows. An intracranial thrombectomy CPT observation does
NOT establish that a particular patient underwent an intervention.
"""
from __future__ import annotations

import argparse
import csv
from contextlib import closing
import io
import json
from pathlib import Path
import sqlite3
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PRIVATE_ROOT=ROOT/"results/phase1/full_reconstruction_private"
ACK="I_CONFIRM_INTERNAL_REVIEW_ONLY"
EXPECTED=("medication_drug.csv","medication_ingredient.csv", "encounter.csv")
CPT_STROKE_THROMBECTOMY=("61645",)
EXCLUDED_PERIPHERAL=("37184",)
MAX_HEADER=131072
MAX_ENTRIES=300


def columns_only(z:zipfile.ZipFile, file_name:str)->tuple[str,...] | None:
    matches=[i for i in z.infolist()
             if i.filename.replace("\\","/").rsplit("/",1)[-1].lower()==file_name]
    if len(matches)>1:
        raise ValueError("Ambiguous duplicate source member")
    if not matches:
        return None
    if matches[0].is_dir():
        raise ValueError("File member unexpectedly a directory")
    with z.open(matches[0]) as handle:
        head=handle.readline(MAX_HEADER+1)
    if len(head)>MAX_HEADER or not head.endswith((b"\n",b"\r")):
        raise ValueError("Overlarge or unterminated CSV header")
    row=next(csv.reader([head.decode("utf-8-sig").rstrip("\r\n")],strict=True))
    if not row or len(row)>1024 or any(not f.strip() for f in row):
        raise ValueError("Invalid clinical table header")
    return tuple(row)


def metadata(archive:Path, step36:dict)->dict:
    if step36.get("stage")!="STEP36_RESEARCH_METADATA_PREFLIGHT":
        raise ValueError("Expected verified Step36 inventory")
    if not step36.get("files",{}).get("procedure.csv",{}).get("present"):
        raise ValueError("Original procedure preflight missing")
    with zipfile.ZipFile(archive) as z:
        csv_items=[i for i in z.infolist() if i.filename.lower().endswith(".csv")]
        if len(csv_items)>MAX_ENTRIES:
            raise ValueError("Source ZIP has too many members")
        for required in ("procedure.csv","encounter.csv","patient.csv","diagnosis.csv"):
            cols=columns_only(z,required)
            if cols is None:
                raise ValueError("Required provenance member absent: "+required)
            expected=step36["files"].get(required,{})
            if list(cols)!=expected.get("headers"):
                raise ValueError("Original source columns differ from preflight")
            candidates=[i for i in csv_items if i.filename.replace("\\","/").rsplit("/",1)[-1].lower()==required]
            if len(candidates)!=1 or candidates[0].file_size != expected.get("uncompressed_bytes"):
                raise ValueError("Original source file size mismatch")
        result={}
        for name in EXPECTED:
            cols=columns_only(z,name)
            if cols is None:
                result[name]={"available":False}
                continue
            low=[s.lower() for s in cols]
            result[name]={
                "available":True,
                "has_patient_id":"patient_id" in low,
                "has_encounter_id":"encounter_id" in low,
                "has_temporal_field":any("date" in f or "time" in f for f in low),
                "has_code_or_drug_field":any("code" in f or "drug" in f or "ingredient" in f for f in low),
                "columns":list(cols),
            }
        return result


def code_profile(db:sqlite3.Connection)->dict:
    # The Step68 profile counts *procedure source rows*, NOT treated patients.
    rows=db.execute(
        "SELECT code, scope, service_year, SUM(n) FROM code_profile "
        "WHERE system='CPT' AND code IN ('61645','37184') "
        "GROUP BY code,scope,service_year ORDER BY code,scope,service_year"
    ).fetchall()
    data={c:{"source_rows_total":0,"index_or_other_day0_rows":0,
             "service_years":set()} for c in CPT_STROKE_THROMBECTOMY+EXCLUDED_PERIPHERAL}
    for code,scope,year,n in rows:
        if code not in data or int(n)<0:
            raise ValueError("Invalid source code aggregate")
        data[code]["source_rows_total"]+=int(n)
        if scope in ("INDEX_IMP","NONIMP_DAY0"):
            data[code]["index_or_other_day0_rows"]+=int(n)
        data[code]["service_years"].add(str(year))
    for v in data.values():
        v["service_years"]=sorted(v["service_years"])
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip",type=Path,required=True)
    p.add_argument("--step36",type=Path,
                   default=ROOT/"results/phase1/step36_research_metadata_preflight.json")
    p.add_argument("--acknowledge",required=True)
    args=p.parse_args()
    if args.acknowledge!=ACK:
        p.error("Explicit local-only review acknowledgment required")
    for file in (args.zip,args.step36):
        if file.is_symlink() or not file.is_file():
            raise FileNotFoundError("Source ZIP or Step36 preflight absent")
    inv=json.loads(args.step36.read_text(encoding="utf8"))
    med=metadata(args.zip,inv)
    from_path=PRIVATE_ROOT/"step68_procedure_windows_private/step68_procedure_windows_LOCAL_ONLY.sqlite"
    if from_path.is_symlink() or not from_path.is_file():
        raise FileNotFoundError("Frozen Step68 code profile checkpoint unavailable")
    with closing(sqlite3.connect("file:"+str(from_path.resolve())+"?mode=ro",uri=True)) as db:
        prior=db.execute("SELECT v FROM meta WHERE k='frozen'").fetchone()
        if prior is None:
            raise ValueError("Step68 frozen state unverified")
        code=code_profile(db)
    print("STEP89 LOCAL ONLY: bounded metadata/treatment coding feasibility review")
    print("Original procedure/medication source rows read: 0")
    for name,obj in sorted(med.items()):
        print(name, "AVAILABLE" if obj["available"] else "ABSENT",
              "patient/encounter/time/code fields:",
              "/".join("YES" if obj.get(key,False) else "NO" for key in
                       ("has_patient_id","has_encounter_id","has_temporal_field","has_code_or_drug_field")))
    print("Intracranial thrombectomy candidate CPT in frozen indexed profile:",
          "PRESENT" if code["61645"]["index_or_other_day0_rows"]>0 else "NOT SEEN")
    print("Peripheral thrombectomy 37184 excluded from intracranial positive control")
    print("No drug administration status or patient-level therapy outcome established")
    print("No source rescan started. Coded treatment requires clinical/codebook adjudication.")

if __name__=="__main__":
    main()