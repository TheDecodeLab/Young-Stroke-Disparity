# Publication release audit, 2026-11-02

**Status: BLOCKED.** Audit of the live public GitHub repository `TheDecodeLab/Young-Stroke-Disparity`. This document is a source-control safety audit, not a dataset-use authorization or manuscript peer review.

## Git branches and pull requests

- Default branch: `master`. Audited head `ecbed66f9a017ed51ace7258c8c0e5a24e58bee2`.
- Research development branch: `analysis-rebuild-phase1-audit`. Audited head `71503f08ad8c4b6c0788fab628bbb4df4e4426fe`.
- Comparison at audit: development was 679 commits ahead, zero commits behind. There was no divergent branch history or merge conflict.
- One open pull request: [#1](https://github.com/TheDecodeLab/Young-Stroke-Disparity/pull/1), marked draft with an explicit **DO NOT MERGE** governance warning. No other open pull requests or additional branches were found.
- This audit does not inspect uncommitted changes on individual workstations. Use `git status --short` and `git branch -vv` on each clone.

**Decision:** Do not merge PR #1, change the default branch, rewrite history, or delete the development branch until the current and historic data exposure is resolved. No branch is redundant until the one unmerged branch is safely integrated.

## Release blockers, by priority

1. **Legacy tracked research-derived patient records.** Both current branches contain `dataset/df_trinetx_total_young.parquet`. The earlier [Phase 1 audit](PHASE1_AUDIT.md) explicitly describes it as patient-level. This is not a safe public code-release artifact absent verified redistribution authorization.
2. **Legacy notebook stored results.** Both current branches contain `disparity_young-claen.ipynb`. The earlier audit identifies displayed pseudonymous patient IDs and postal codes in notebook outputs. Remove or strip those outputs for any clean publication snapshot after confirming scientific archival requirements.
3. **Prior commits and public caches.** The open PR documents a manuscript draft briefly committed and removed from the present tip. File deletion from HEAD, adding `.gitignore` patterns, and ordinary merge commits cannot remove history exposure. An authorized remediation may require `git-filter-repo`, coordinated clone resets and GitHub Support cache/PR-reference cleanup, or a new publication repository initialized from a reviewed safe snapshot. See [GitHub's official sensitive-data history removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
4. **Historical results files.** The checked-in NIS summary CSVs and older derived CPT count aggregate were not reverified for a public code release. Release approval must cover cumulative and complementary disclosure, provenance and applicable third-party terms. The current manuscript uses Research Network data and does not validate the old NIS comparisons.
5. **CI infrastructure.** Several recent GitHub Actions jobs failed *before the tests started*. The runner was Ubuntu 26.04 but the workflows requested Python 3.9, which was unavailable. This failure is distinct from a failed statistical test. Updated workflows use a pinned Ubuntu 24.04 runner and Python 3.11. Green full-suite CI after this change remains to be verified.
6. **Scientific publication gates.** Verify the current 14-code CPT dictionary against historical annual versions, confirm actual data source and release rights, and close manuscript ethics, funding, data availability, and author declarations. Approval to access Research Network data is not automatically authorization to redistribute patient-level derivatives. Do not claim journal-readiness based solely on Git cleanup.

## Automated safety checks

The publication branch adds [`scripts/check_public_release_tree.py`](../scripts/check_public_release_tree.py), tested on fabricated paths and notebooks. It inspects tracked filenames and whether tracked notebooks contain saved execution outputs. It does not open binary datasets or print clinical values. It fails closed for tracked Parquet and similar binaries, private paths, output-bearing notebooks and selected historical study aggregates requiring review. A passing run cannot certify history, copyright, missing HCO metadata or institutional release permission.

The new [`publication_release_gate.yml`](../.github/workflows/publication_release_gate.yml) runs this check and the synthetic test suite. Existing synthetic workflows have their Python/runner setup updated. Publication remains blocked until the tracked-file gate and all applicable author/institutional checks pass.

## Proposed safe branch consolidation

**Gate A: Authorize release scope.** Determine which current and historical materials may remain public. Obtain an institutional/data-steward decision for the legacy patient-level file and notebook examples. This is **not** a request for a new Research Network access application. If those records were not authorized for public sharing, follow the incident-response process required by the applicable institutional policy.

**Gate B: Remediate data and Git history.** Prepare a reviewed, code-only publication tree. If history rewrite is authorized, coordinate it with all collaborators and GitHub Support as appropriate. Alternatively, publish a new, freshly initialized, code-only repository rather than inheriting tainted history. Keep the old repository under the disposition recommended by the institution. Check all branch, tag and pull-request refs and caches. Do not force-push the existing public history without that coordination.

**Gate C: Verify software and analysis reproduction.** Run the full synthetic suite on the release tree and selected frozen-checkpoint analyses on an authorized workstation. Confirm scripts, requirements, README, codebook provenance, release documentation, citation and figure reproducibility. No clinical data in CI artifacts, screenshots or logs.

**Gate D: Merge, retire, and tag.** Only after A-C succeed, merge the approved development changes to the intended default branch through the reviewed PR, verify the resulting SHA and tests, then delete the merged feature branch. The connected GitHub tools do not currently expose a branch deletion operation. Once approved and merged, an authorized local command such as `git push origin --delete analysis-rebuild-phase1-audit` can delete the remote branch. Do not run it before the merge, clearance and history review.

## Audit basis and limits

Verified directly using repository metadata, branch comparisons, PR #1, Git trees, `.gitignore`, README, the Phase 1 audit and GitHub Actions job logs. The notebook and legacy patient-level Parquet were **not downloaded or inspected for individual rows**. The safety interpretation follows the repository's own prior audit and explicit PR restrictions. This audit does not establish whether a specific dataset redistribution agreement has been signed, whether historical source code has outstanding licensing issues, or whether private local clones have uncommitted work.
