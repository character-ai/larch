### FINDING_10: [OUT_OF_SCOPE] Bash path lacks volatile-only skip behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-runlog-porcelain-output.txt
- **Severity**: latent
- **Concern**: Bash `larch-log.sh` still commits refresh churn without the new volatile-only classify/restore path, creating bash/python divergence until cutover or parity work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-runlog-porcelain-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_14: [OUT_OF_SCOPE] Parity-file monkeypatch cleanup treated as optional by one reviewer
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: One reviewer marked stale `test_merge_bash_parity.py` flush monkeypatches as non-regressing/optional cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_23: [OUT_OF_SCOPE] main catch-all JSON envelope also noted as pre-existing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A reviewer separately marked broad exception-to-JSON handling as pre-existing/out-of-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_24: [OUT_OF_SCOPE] CI breadcrumbs may stay silent before first wait
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Breadcrumbs only emit on the wait branch, so some immediate decisions can lack an initial progress line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_25: [OUT_OF_SCOPE] Workflow automation docs omit Python 3.11+ ship requirement
- **Reviewer(s)**: dyn-runtime-compat-output.txt
- **Severity**: nit
- **Concern**: Installation/setup workflow automation prerequisites do not mention Python 3.11+ for the future Python ship driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-compat-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_26: [OUT_OF_SCOPE] Runtime floor propagation otherwise appears consistent
- **Reviewer(s)**: dyn-runtime-compat-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted floor propagation across Python config, docs, report-tokens, and CI appears internally aligned, with no 3.12-only syntax found.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-compat-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_29: [OUT_OF_SCOPE] Python ensure_pr omits explicit --base
- **Reviewer(s)**: dyn-gh-cli-contract-output.txt
- **Severity**: latent
- **Concern**: `ensure_pr` does not pass an explicit base to `gh.pr_create`, unlike bash; reviewer marked it pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-contract-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_30: [OUT_OF_SCOPE] Success-path post-create list failure branch lacks test
- **Reviewer(s)**: dyn-gh-cli-contract-output.txt
- **Severity**: nit
- **Concern**: rc=0 create with failing post-create `pr list` plus stdout URL is not tested, though code appears correct on inspection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_33: [OUT_OF_SCOPE] Duplicate closed-PR noop checks remain
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: nit
- **Concern**: `_merge_noop_if_pr_closed` is called twice back-to-back after pre-merge flush removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


