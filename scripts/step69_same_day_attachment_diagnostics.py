#!/usr/bin/env python3
"""Step69: LOCAL-ONLY no-rescan investigation of same-day non-index CPT14.

Reads frozen Step62/63/68 private SQLite files in query-only mode.
Does NOT classify ICD-10-PCS candidates as performed imaging.
Prints grouped source-QA counts, never patients, encounters or exact code strings.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3

try:
    from scripts import step62_checkpointed_cohort as s62
    from scripts import step63_ed_encounter_feasibility as s63
    from scripts import step64_ed_capture_ceiling as s64
    from scripts import step68_joint_imaging_window_scan as s68
except ModuleNotFoundError:
    import step62_checkpointed_cohort as s62
    import step63_ed_encounter_feasibility as s63
    import step64_ed_capture_ceiling as s64
    import step68_joint_imaging_window_scan as s68

MODALITIES = tuple(sorted(set(s62.CPT.values())))
WINDOWS = ("IMP", "ED", "ED_F", "DAY0", "PRE2", "POST2", "PRE7")
B_GROUP_SCOPES = ("INDEX_IMP", "NONIMP_DAY0", "UNIQUE_ED")
COUNTER_FIELDS = ("n","inpatient","other_day0","new_other_day0",
                  "new_other_day0_not_ED","new_other_day0_unlinked",
                  "ed","new_ed","new_ed_f","ed_new_and_day0",
                  "pre2","new_pre2","post2","new_post2","pre7","new_pre7",
                  "union_ed_or_day0","union_ed_or_pre2_day0",
                  "union_ed_or_pre7_day0","union_ed_or_pre2_day0_post2")


def _add(out, kind, label, bits, linked):
    """One patient contributes once to each disjoint group."""
    m = bits
    imp=bool(m & s68.IMP)
    ed=bool(m & s68.ED)
    ed_f=bool(m & s68.ED_F)
    day0=bool(m & s68.NONIMP_DAY0)
    pre2=bool(m & s68.NONIMP_PRE2)
    post2=bool(m & s68.NONIMP_POST2)
    pre7=bool(m & s68.NONIMP_PRE7)
    if ed_f and not ed:
        raise ValueError("ED_F mask absent ED flag")
    if ed and not linked:
        raise ValueError("Stored ED CPT14 code has no frozen Step63 unique link")
    c=out[(kind,label)]
    c["n"]+=1
    for key,v in (
        ("inpatient",imp),("other_day0",day0),
        ("new_other_day0",day0 and not imp),
        ("new_other_day0_not_ED",day0 and not imp and not ed),
        ("new_other_day0_unlinked",day0 and not imp and not linked),
        ("ed",ed),("new_ed",ed and not imp),
        ("new_ed_f",ed_f and not imp),
        ("ed_new_and_day0",ed and day0 and not imp),
        ("pre2",pre2),("new_pre2",pre2 and not imp),
        ("post2",post2),("new_post2",post2 and not imp),
        ("pre7",pre7),("new_pre7",pre7 and not imp),
        ("union_ed_or_day0",(ed or day0) and not imp),
        ("union_ed_or_pre2_day0",(ed or pre2 or day0) and not imp),
        ("union_ed_or_pre7_day0",(ed or pre7 or day0) and not imp),
        ("union_ed_or_pre2_day0_post2",
         (ed or pre2 or day0 or post2) and not imp)):
        c[key]+=int(v)


def aggregate(db):
    """One read-only SQL stream, collapsed at indexed-patient/cohort grain."""
    sql = """
      SELECT i.cohort,i.patient,substr(i.start,1,4),i.principal,
             CASE WHEN l.patient IS NULL THEN 0 ELSE 1 END linked,
             CASE WHEN EXISTS(
               SELECT 1 FROM main.ambiguous a WHERE a.patient=i.patient)
               THEN 1 ELSE 0 END held,
             f.modality,f.mask
      FROM main.idx i
      LEFT JOIN main.linked l
        ON l.cohort=i.cohort AND l.patient=i.patient
      LEFT JOIN capture.flags f
        ON f.cohort=i.cohort AND f.patient=i.patient
      ORDER BY i.cohort,i.patient
    """
    counts=defaultdict(Counter)
    previous=None
    modality_bits={}
    details=None
    def flush():
        if details is None:
            return
        cohort,year,P,linked,held=details
        bit=0
        for m in modality_bits.values():
            bit |= m
        categories=(
            ("COHORT",cohort),
            ("P",cohort+"|P="+str(P)),
            ("YEAR_P",cohort+"|"+year+"|P="+str(P)),
            ("EDLINK_P",cohort+"|P="+str(P)+"|"+(
                "UNIQUE_ED" if linked else "NO_UNIQUE_ED")),
            ("QUARANTINE_P",cohort+"|P="+str(P)+"|"+(
                "ANY_AMBIG" if held else "NONE")),
        )
        for group in categories:
            _add(counts,*group,bit,linked)
        for modality in MODALITIES:
            _add(counts,"MODALITY_P",cohort+"|P="+str(P)+"|"+modality,
                 modality_bits.get(modality,0),linked)
    for cohort,p,yr,P,linked,held,modality,mask in db.execute(sql):
        key=(cohort,p)
        if key!=previous:
            flush()
            previous=key
            details=(cohort,yr,int(P),bool(linked),bool(held))
            modality_bits={}
        if modality is not None:
            if modality not in MODALITIES or modality in modality_bits:
                raise ValueError("Unexpected repeated/non-CPT14 modality")
            modality_bits[modality]=int(mask)
    flush()
    return counts


def verify_aggregate(db,counts,reference=None):
    """Reconcile primary captured outcomes to independent frozen sources."""
    status=db.execute("SELECT seen,done FROM capture.progress "
                      "WHERE stage='procedure'").fetchone()
    if status is None or status[1]!=1 or status[0]!=993025015:
        raise ValueError("Step68 source procedure checkpoint incomplete")
    if not counts:
        raise ValueError("Empty Step69 analysis")
    for cohort in s62.COHORTS:
        key=("COHORT",cohort)
        n=db.execute("SELECT COUNT(*) FROM main.idx WHERE cohort=?",
                     (cohort,)).fetchone()[0]
        baseline=db.execute("""
            SELECT COUNT(*) FROM baseline.idx i WHERE i.cohort=?
            AND EXISTS(SELECT 1 FROM baseline.image im
                  WHERE im.cohort=i.cohort AND im.patient=i.patient)
        """,(cohort,)).fetchone()[0]
        c=counts[key]
        if n!=c["n"] or baseline!=c["inpatient"]:
            raise ValueError("Step69 disagrees with frozen Step62/63 index baseline")
        p_groups=[counts[("P",cohort+"|P="+str(p))] for p in (0,1)]
        for measure in COUNTER_FIELDS:
            if sum(x[measure] for x in p_groups)!=c[measure]:
                raise AssertionError("Step69 P groups do not reconcile")
        if reference is not None:
            row=reference["patient_cohort_aggregates"]["COHORT|"+cohort]
            comparisons={
                "n":"n","imp":"inpatient",
                "new_ed":"new_ed",
                "new_ed_f":"new_ed_f",
                "new_day0_other":"new_other_day0",
                "new_pre2":"new_pre2",
                "new_post2_other":"new_post2",
                "new_pre7":"new_pre7",
                "new_ed_or_pre2_day0":"union_ed_or_pre2_day0",
                "new_ed_or_pre7_day0":"union_ed_or_pre7_day0",
                "new_ed_or_pre2_day0_post2":"union_ed_or_pre2_day0_post2",
            }
            for old,now in comparisons.items():
                if int(row.get(old,0))!=c[now]:
                    raise ValueError("Step69 vs Step68 aggregate discrepancy: "+old)
        if not (0<=c["new_ed"]<=c["ed"]<=c["n"]
                and 0<=c["new_other_day0_unlinked"]<=
                    c["new_other_day0_not_ED"]<=c["new_other_day0"]
                and c["inpatient"]+c["union_ed_or_day0"]<=c["n"]):
            raise AssertionError("Step69 nested denominators failed")
    return True


def pct(a,n):
    return 100.0*a/n if n else 0.0


def display(counts):
    print("STEP69 LOCAL ONLY: frozen CPT14 patient-level encounter hypothesis audit")
    print("OTHER_DAY0 is another encounter, NOT a verified ED or same-hospital episode.")
    print("P=0 includes S/blank/unmarked. No causal, performed-scan, or site claims.")
    for kind in ("P","EDLINK_P","QUARANTINE_P","YEAR_P","MODALITY_P"):
        print("\nBY",kind)
        for (k,label),c in sorted(counts.items()):
            if k!=kind:
                continue
            if c["n"]<11:
                print("Suppressed group n<11")
                continue
            n=c["n"]
            base=c["inpatient"]
            day=c["new_other_day0"]
            print(label,
                  "n",n,
                  "IMP",base,"IMP_pct","%.2f"%pct(base,n),
                  "DAY0_other_new",day,"DAY0_gain_pp","%.2f"%pct(day,n),
                  "IMP_or_DAY0_pct","%.2f"%pct(base+day,n),
                  "DAY0_new_no_ED_link",c["new_other_day0_unlinked"],
                  "DAY0_new_not_ED_code",c["new_other_day0_not_ED"],
                  "ED_new",c["new_ed"],
                  "ED_overlap_DAY0",c["ed_new_and_day0"],
                  "pre2_new",c["new_pre2"],
                  "post2_new",c["new_post2"],
                  "ED_or_pre2_day0_new",c["union_ed_or_pre2_day0"],
                  "ED_or_pre7_day0_new",c["union_ed_or_pre7_day0"],
                  "ED_or_pre2_day0_post2_new",
                  c["union_ed_or_pre2_day0_post2"])
    print("\nP-CONTRAST (UNADJUSTED, percentage points)")
    for cohort in s62.COHORTS:
        a=counts[("P",cohort+"|P=0")]
        b=counts[("P",cohort+"|P=1")]
        print(cohort,"P1_minus_P0_original_pp",
              "%.2f"%(pct(b["inpatient"],b["n"])-pct(a["inpatient"],a["n"])),
              "P1_minus_P0_IMP_or_DAY0_pp",
              "%.2f"%(pct(b["inpatient"]+b["new_other_day0"],b["n"])
                         -pct(a["inpatient"]+a["new_other_day0"],a["n"])))
    print("All groups are cohort-memberships, not additive across cohort definitions.")


def code_family_discovery(db):
    """Aggregate exact-code *rows* to illustrative PCS B-prefix families.

    PCS section B candidates are NOT validated brain imaging outcomes.
    The source may include invalid, deidentified or version-specific codes.
    """
    b=Counter()
    all_rows=Counter()
    shapes=Counter()
    prefixes=Counter()
    for code,scope,yr,P,n in db.execute("""
        SELECT code,scope,service_year,P,n FROM capture.code_profile
        WHERE system='ICD-10-PCS' AND scope IN
          ('INDEX_IMP','NONIMP_DAY0','UNIQUE_ED')
    """):
        key=(scope,int(P),str(yr))
        all_rows[key]+=int(n)
        if len(code)==7 and code.isascii() and code.isalnum():
            shapes[key]+=int(n)
            if code.startswith("B"):
                b[key]+=int(n)
                prefixes[(scope,int(P),code[:3])]+=int(n)
    print("\nPCS SOURCE-ROW DISCOVERY (NOT validated procedures/patients)")
    for scope in B_GROUP_SCOPES:
        for P in (0,1):
            keys=[(scope,P,str(y)) for y in range(2016,2025)]
            print(scope,"P",P,
                  "all_PCS_rows",sum(all_rows[k] for k in keys),
                  "seven_char_rows",sum(shapes[k] for k in keys),
                  "B_prefix_rows_unreviewed",sum(b[k] for k in keys))
            top=sorted(
                ((key[2],value) for key,value in prefixes.items()
                 if key[0]==scope and key[1]==P and value>=11),
                key=lambda z:(-z[1],z[0]))[:8]
            print("  top_3_char_families_unreviewed:",
                  " ".join(x+":"+str(n) for x,n in top) or "none>=11")
    print("INDEX_IMP PCS B-like source rows by service year and P:")
    for yr in range(2016,2025):
        for P in (0,1):
            key=("INDEX_IMP",P,str(yr))
            if all_rows[key] >= 11:
                print(yr,"P",P,"all_PCS",all_rows[key],
                      "B_prefix_unreviewed",b[key])
    print("Never interpret a B-prefix hit as an MRI/CT without a year-specific codebook.")


def main():
    paths=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError("Completed private Step62/63/68 SQLite path missing")
    db62,db63,db68=(p.resolve() for p in paths)
    if db62==db63 or db62==db68 or db63==db68:
        raise ValueError("Unexpected identical private databases")
    report=s68.PRIVATE/s68.REPORT
    if report.is_symlink() or not report.is_file():
        raise FileNotFoundError("Completed local-only Step68 aggregate JSON required")
    published=json.loads(report.read_text(encoding="utf8"))
    if published.get("stage")!=s68.POLICY:
        raise ValueError("Step68 report policy mismatch")
    with sqlite3.connect("file:"+str(db63)+"?mode=ro",uri=True) as db:
        db.execute("ATTACH DATABASE ? AS baseline",
                   ("file:"+str(db62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",
                   ("file:"+str(db68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,db62,db63)
        saved=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if saved is None:
            raise ValueError("Missing Step68 frozen snapshot")
        meta=json.loads(saved[0])
        if meta.get("policy")!=s68.POLICY or (
            meta.get("s62") != s68._snapshot(db62)
            or meta.get("s63") != s68._snapshot(db63)):
            raise ValueError("Step68 source database snapshot mismatch")
        c=aggregate(db)
        verify_aggregate(db,c,published)
        display(c)
        code_family_discovery(db)
    print("\nTERMINAL OUTPUT ONLY; do not upload private databases or code profiles.")


if __name__=="__main__":
    main()
