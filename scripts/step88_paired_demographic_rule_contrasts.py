#!/usr/bin/env python3
"""Step88: paired, patient-equivalent bootstrap of CPT capture by encounter rule.

Reads frozen Step62/63/68 private checkpoints via Step82, with no source ZIP scan.
The bootstrap samples the joint distribution of covariates and the nested
pair of outcomes, hence is exactly equivalent to sampling deidentified
patient observations with replacement, after sufficient-statistic grouping.
No patient identifiers or individual-level observations are written.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import stat
import warnings

import numpy as np
import pandas as pd
from patsy import build_design_matrices, dmatrix
from scipy.special import expit
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT / "results/phase1/full_reconstruction_private"
OUTPUT = PRIVATE_ROOT / "step88_paired_demographics_private/paired_rule_contrasts_LOCAL_ONLY.json"
ACK = "I_CONFIRM_INTERNAL_REVIEW_ONLY"
REQUIRED_FIELDS = ("sex", "race", "ethnicity", "year", "age_band", "P", "held", "n")
COMPARISONS = (
    ("sex", "MALE", "FEMALE"),
    ("race", "WHITE", "BLACK_AFRICAN_AMERICAN"),
    ("ethnicity", "NOT_HISPANIC_LATINO", "HISPANIC_LATINO"),
)
SCOPES = ("quality", "complete_demographics")
OUTCOMES = ("any", "advanced")
THRESHOLD = 11
Z = 1.959963984540054


def dependencies():
    try:
        from scripts import step62_checkpointed_cohort as s62
        from scripts import step63_ed_encounter_feasibility as s63
        from scripts import step64_ed_capture_ceiling as s64
        from scripts import step68_joint_imaging_window_scan as s68
        from scripts import step82_demographic_definition_sensitivity as s82
    except ModuleNotFoundError as exc:
        if exc.name != "scripts":
            raise
        import step62_checkpointed_cohort as s62
        import step63_ed_encounter_feasibility as s63
        import step64_ed_capture_ceiling as s64
        import step68_joint_imaging_window_scan as s68
        import step82_demographic_definition_sensitivity as s82
    return s62, s63, s64, s68, s82


def scoped(table: pd.DataFrame, scope: str) -> pd.DataFrame:
    if scope not in SCOPES:
        raise ValueError("Unknown scope")
    missing = set(REQUIRED_FIELDS) - set(table.columns)
    if missing:
        raise ValueError("Missing required covariates: " + ",".join(sorted(missing)))
    x = table.copy()
    if scope == "complete_demographics":
        for col in ("sex", "race", "ethnicity"):
            x = x.loc[~x[col].isin(("UNKNOWN_MISSING", "OTHER_OR_UNMAPPED"))].copy()
    if x.empty or int(x.n.sum()) < 100:
        raise ValueError("Insufficient scope population")
    if any(x.n.astype(int) <= 0):
        raise ValueError("Nonpositive group sizes")
    return x.reset_index(drop=True)


def joint_counts(x: pd.DataFrame, outcome: str) -> np.ndarray:
    """Columns (0,0), (0,1), (1,1), where rule1 <= rule2."""
    if outcome not in OUTCOMES:
        raise ValueError("Invalid outcome")
    a = x[outcome + "_imp"].to_numpy(dtype=np.int64)
    b = x[outcome + "_day0"].to_numpy(dtype=np.int64)
    n = x.n.to_numpy(dtype=np.int64)
    if np.any(a < 0) or np.any(b < a) or np.any(b > n):
        raise ValueError("Rule nesting violated")
    return np.column_stack((n - b, b - a, a))


def compatible_support(x: pd.DataFrame, pair: np.ndarray, field: str,
                       ref: str, alt: str) -> bool:
    """Check both outcomes, gained events, complements and P/ambiguity support."""
    if field not in ("sex", "race", "ethnicity"):
        raise ValueError("Not a prespecified demographic")
    if set((ref, alt)) - set(x[field]):
        return False
    n = pair.sum(axis=1)
    k0 = pair[:, 2]
    k1 = pair[:, 1] + k0
    gain = pair[:, 1]
    for level in (ref, alt):
        idx = (x[field] == level).to_numpy()
        den = int(n[idx].sum())
        if den < 2 * THRESHOLD:
            return False
        for k in (int(k0[idx].sum()), int(k1[idx].sum()), int(gain[idx].sum())):
            if min(k, den - k) < THRESHOLD:
                return False
        for p in (0, 1):
            for held in (0, 1):
                mask = idx & (x.P.to_numpy() == p) & (x.held.to_numpy() == held)
                if int(n[mask].sum()) < THRESHOLD:
                    return False
    return True


def design_for_scope(x: pd.DataFrame):
    formula = "C(sex)+C(race)+C(ethnicity)+C(year)+C(age_band)+P+held"
    frame = dmatrix(formula, x, return_type="dataframe")
    design_info = frame.design_info
    X = frame.to_numpy(dtype=float)
    if np.linalg.matrix_rank(X) != X.shape[1]:
        raise ValueError("Covariate design rank deficient")
    # Do not allow a different formula in the bootstrap.
    return X, design_info


def fit_grouped(X: np.ndarray, n: np.ndarray, k: np.ndarray) -> np.ndarray:
    idx = n > 0
    if np.count_nonzero(idx) <= X.shape[1] or np.any(k[idx] < 0) or np.any(k[idx] > n[idx]):
        raise ValueError("Invalid binomial support")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fit = sm.GLM(k[idx] / n[idx], X[idx],
                     family=sm.families.Binomial(),
                     var_weights=n[idx]).fit(maxiter=100, disp=False)
    params = np.asarray(fit.params, dtype=float)
    if (not fit.converged or not np.isfinite(params).all() or
            np.max(np.abs(params)) > 24 or
            any("PerfectSeparation" in type(w.message).__name__ for w in caught)):
        raise ValueError("Unstable grouped-binomial fit")
    return params


def counterfactual_designs(x: pd.DataFrame, design_info, field: str,
                           ref: str, alt: str):
    frames = []
    for category in (ref, alt):
        cf = x.copy()
        cf[field] = category
        frames.append(np.asarray(build_design_matrices([design_info], cf)[0], dtype=float))
    return frames


def paired_contrast(X: np.ndarray, n: np.ndarray, pair: np.ndarray,
                    cf_ref: np.ndarray, cf_alt: np.ndarray) -> np.ndarray:
    """Array of reference and alternative risks, two differences, and their change.

    All results in percentage points. Rule outcomes are modeled separately,
    but the bootstrap resamples the *joint* paired outcome states.
    """
    if not np.array_equal(n, pair.sum(axis=1)):
        raise ValueError("Bootstrap denominators and joint states disagree")
    betas = (fit_grouped(X, n, pair[:, 2]),
             fit_grouped(X, n, pair[:, 2] + pair[:, 1]))
    outputs = []
    for beta in betas:
        r = 100 * float(n @ expit(cf_ref @ beta) / n.sum())
        a = 100 * float(n @ expit(cf_alt @ beta) / n.sum())
        outputs.extend((r, a, a-r))
    outputs.append(outputs[5]-outputs[2])
    return np.asarray(outputs, dtype=float)


def analyze(table: pd.DataFrame, outcome: str, scope: str,
            draws: int, seed: int,
            comparisons=COMPARISONS) -> dict:
    """Full bootstrap resamples covariate + pair-outcome tuples jointly.

    A multinomial draw over grouped (covariates, joint outcome) states is
    algebraically identical to a nonparametric patient-level paired bootstrap.
    It is *not* a separate binomial draw for each rule and it does not fix the
    patient covariate distribution in bootstrap resamples.
    """
    if draws < 19 or draws > 5000:
        raise ValueError("Bootstrap iterations must be 19..5000")
    x = scoped(table, scope)
    pair = joint_counts(x, outcome)
    n = pair.sum(axis=1)
    X, info = design_for_scope(x)
    N = int(n.sum())
    probabilities = pair.flatten().astype(float) / N
    if not np.isclose(probabilities.sum(), 1):
        raise ValueError("Grouped joint probability mass missing")
    supported = []
    for field, ref, alt in comparisons:
        if compatible_support(x, pair, field, ref, alt):
            r, a = counterfactual_designs(x, info, field, ref, alt)
            supported.append((field, ref, alt, r, a))
    if not supported:
        raise ValueError("No disclosure-safe comparisons")
    estimates = {(field,ref,alt):paired_contrast(X,n,pair,mat0,mat1)
                 for field,ref,alt,mat0,mat1 in supported}
    samples = {key:[] for key in estimates}
    failed=0
    rng=np.random.default_rng(seed)
    for _ in range(draws):
        replicate = rng.multinomial(N, probabilities).reshape(-1, 3)
        reps_n=replicate.sum(axis=1)
        try:
            betas = (fit_grouped(X, reps_n, replicate[:,2]),
                     fit_grouped(X, reps_n, replicate[:,2] + replicate[:,1]))
        except (ValueError, RuntimeError, np.linalg.LinAlgError):
            failed += 1
            continue
        for field,ref,alt,mat0,mat1 in supported:
            vals=[]
            for beta in betas:
                v0=100*float(reps_n @ expit(mat0 @ beta) / N)
                v1=100*float(reps_n @ expit(mat1 @ beta) / N)
                vals.extend((v0,v1,v1-v0))
            vals.append(vals[5]-vals[2])
            samples[(field,ref,alt)].append(vals)
    valid = draws - failed
    if valid < max(19, int(0.95 * draws)):
        raise ValueError("Too many failed paired bootstrap fits")
    labels=("rule1_reference_pct","rule1_target_pct","rule1_RD_pp",
            "rule2_reference_pct","rule2_target_pct","rule2_RD_pp","change_RD_pp")
    result={"scope":scope, "outcome":outcome, "cohort_n":N,
            "grouped_strata":len(x), "requested_bootstraps":draws,
            "valid_bootstraps":valid,"seed":seed,
            "resampling":"paired_multinomial_over_joint_patient_states",
            "confidence_intervals":"percentile_95pct_patient_independence_working_model",
            "comparisons":[]}
    for field,ref,alt,_,_ in supported:
        key=(field,ref,alt)
        boots=np.asarray(samples[key],dtype=float)
        if boots.shape!=(valid,7):
            raise ValueError("Incomplete bootstrap contrast matrix")
        lower,upper=np.percentile(boots,[2.5,97.5],axis=0)
        sd=boots.std(axis=0,ddof=1)
        point=estimates[key]
        row={"field":field,"reference":ref,"target":alt,
             "reference_n":int(x.loc[x[field]==ref,"n"].sum()),
             "target_n":int(x.loc[x[field]==alt,"n"].sum())}
        for j,label in enumerate(labels):
            row[label]={"estimate":float(point[j]),
                        "ci_low":float(lower[j]),"ci_high":float(upper[j])}
        # Design effect is a hypothetical variance multiplier, not a cluster adjustment.
        se=float(sd[-1]); effect=float(point[-1])
        row["change_design_effect_to_span_zero"]=(float((abs(effect)/(Z*se))**2)
                                                   if se>0 else None)
        row["change_sensitivity_intervals"]={str(de):[
            float(effect-Z*se*np.sqrt(de)),float(effect+Z*se*np.sqrt(de))]
            for de in (1,2,5,10)}
        result["comparisons"].append(row)
    return result


def save_private(path: Path, result: dict) -> None:
    root = PRIVATE_ROOT.resolve()
    path = path.expanduser()
    target = path.resolve()
    if root not in target.parents or path.is_symlink() or target.exists():
        raise ValueError("Output must be new under private gitignored directory")
    if any(p.is_symlink() for p in path.parents if p.exists() and p != Path("/")):
        raise ValueError("Refusing symlinked ancestor")
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(path.parent,0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,"w",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n")
    os.chmod(path,stat.S_IRUSR | stat.S_IWUSR)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap",type=int,default=399)
    parser.add_argument("--seed",type=int,default=20261101)
    parser.add_argument("--output",type=Path,default=OUTPUT)
    parser.add_argument("--acknowledge",required=True)
    args=parser.parse_args()
    if args.acknowledge!=ACK:
        parser.error("Restricted internal review acknowledgment required")
    s62,s63,s64,s68,s82=dependencies()
    sources=(s62.DB,s63.PRIVATE/s63.DATABASE,s68.PRIVATE/s68.DB)
    if any(p.is_symlink() or not p.is_file() for p in sources):
        raise FileNotFoundError("Frozen Step62/63/68 database absent")
    db62,db63,db68=[p.resolve() for p in sources]
    report=s68.PRIVATE/s68.REPORT
    if report.is_symlink() or not report.is_file():
        raise FileNotFoundError("Frozen Step68 source report missing")
    reference=json.loads(report.read_text(encoding="utf8"))
    if reference.get("stage")!=s68.POLICY:
        raise ValueError("Frozen Step68 policy mismatch")
    with closing(sqlite3.connect("file:"+str(db63)+"?mode=ro",uri=True)) as db:
        db.execute("ATTACH DATABASE ? AS baseline",("file:"+str(db62)+"?mode=ro",))
        db.execute("ATTACH DATABASE ? AS capture",("file:"+str(db68)+"?mode=ro",))
        db.execute("PRAGMA query_only=ON")
        s64.verify(db,db62,db63)
        signature=db.execute("SELECT v FROM capture.meta WHERE k='frozen'").fetchone()
        if not signature:
            raise ValueError("Missing frozen Step68 metadata")
        meta=json.loads(signature[0])
        if (meta.get("policy")!=s68.POLICY or
            meta.get("s62")!=s68._snapshot(db62) or
            meta.get("s63")!=s68._snapshot(db63)):
            raise ValueError("Frozen source signature mismatch")
        state=db.execute("SELECT seen,done FROM capture.progress WHERE stage='procedure'").fetchone()
        if state is None or int(state[1])!=1:
            raise ValueError("Frozen procedure pass incomplete")
        t=s82.group_rows(s82.stream(db))
        s82.verify(t,reference)
    result={"stage":"STEP88_PAIRED_DEMOGRAPHIC_RULE_COMPARISONS_PRIVATE",
            "disclosure_status":"REVIEW_REQUIRED_COMPLETE_PAPER",
            "limitation":"patient-independent bootstrap; no hospital cluster or episode validation",
            "analysis":[]}
    for scope in SCOPES:
        for outcome in OUTCOMES:
            result["analysis"].append(analyze(t,outcome,scope,args.bootstrap,args.seed))
    save_private(args.output,result)
    print("STEP88 LOCAL ONLY: paired adjusted contrasts by encounter rule completed")
    print("Frozen indexed cohort reconciliation: PASS")
    print("Outcomes analyzed:",", ".join(OUTCOMES))
    print("Analysis scopes:",", ".join(SCOPES))
    print("Bootstrap intervals: paired patient-equivalent, not site-clustered")
    print("Results require complete-publication disclosure review")
    print("Private output:",args.output)
    print("No original procedure/medication ZIP rescanned. Do not commit private JSON.")


if __name__=="__main__":
    main()