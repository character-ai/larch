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

### FINDING_34: [OUT_OF_SCOPE] Python OID polling is stricter than bash
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted Python’s new OID polling is stricter than bash and considered an improvement, not a parity regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] config comment still references pre-merge flush
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: nit
- **Concern**: A comment in `python/config.py` still describes pre-merge flush skips even though `merge_pr` no longer calls `flush_logs_pre`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_36: [OUT_OF_SCOPE] Single-CI-cycle convergence test also noted as acceptance gap
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: latent
- **Concern**: Reviewer separately marked missing ship-loop single-CI-cycle convergence coverage as mostly covered by flush removal but still not directly asserted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_39: [OUT_OF_SCOPE] Token/timing sidecars still force substantive commits
- **Reviewer(s)**: dyn-runlog-porcelain-output.txt
- **Severity**: nit
- **Concern**: Token/timing sidecars are excluded from the volatile allowlist, so some pre-push refreshes still commit; reviewer marked this as matching the plan rather than a cleanup bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-porcelain-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_40: [OUT_OF_SCOPE] Final-report warning uses one-off stderr write
- **Reviewer(s)**: dyn-stream-contract-output.txt
- **Severity**: nit
- **Concern**: `write_final_report_comment` warning output does not share `_breadcrumb()` or shared formatting policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_41: [OUT_OF_SCOPE] Python ship lacks report-tokens-style quiet-session handling
- **Reviewer(s)**: dyn-stream-contract-output.txt
- **Severity**: nit
- **Concern**: Report-tokens restores stdout/stderr after lib-quiet, while Python ship has no analogous quiet-session handling; reviewer marked this as possibly intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] ci_monitor stderr helpers diverge from ship breadcrumbs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ci_monitor.py` uses separate stderr helpers, making future operator-facing progress standardization harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

