### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Merge-convergence testing does not prove single CI cycle
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Existing tests only prove `merge_pr` does not call `flush_logs_pre`; they do not catch a `run_ship`-level CI/merge loop regression on a clean green path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: CI poll breadcrumb test omits elapsed seconds
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `python/test_ci_monitor.py` does not assert elapsed seconds in poll breadcrumb output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Raw git porcelain may leak sensitive paths in ShipError detail
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `python/run_logs.py` includes raw git status lines in leftover-porcelain `ShipError` detail, potentially exposing sensitive filenames or paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicate PR JSON parsing in `pr_view_current`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/gh.py` duplicates PullRequest JSON parsing across `pr_view_current`, `pr_view`, and `pr_for_branch`, increasing schema-drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: `pr_create` over-reports `created=True` on recovery
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `python/gh.py` reports `created=True` on success-path recovery even when an open PR already existed, skewing telemetry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_25: Quoted git-status paths fail volatile allowlist classification
- **Reviewer(s)**: dyn-git-porcelain-cleanup-output.txt
- **Severity**: latent
- **Concern**: `_status_line_path` does not strip Git porcelain double quotes, so quoted run-log refresh sidecars may fail `rel/` and allowlist checks and get committed instead of skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-cleanup-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: Malformed or blank porcelain lines fail open to normal commit
- **Reviewer(s)**: dyn-git-porcelain-cleanup-output.txt
- **Severity**: latent
- **Concern**: `_volatile_file_paths` returns `None` for empty/unparseable paths, aborting volatile-only cleanup and falling through to a normal flush commit rather than failing closed or distinguishing non-volatile paths from parse failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-cleanup-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicated post-create PR resolution cascade
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/gh.py` duplicates PR recovery logic on conflict and success paths, risking inconsistent fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Large volatile-run-log cleanup block is hard to maintain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `python/run_logs.py` embeds a large volatile-only porcelain/cleanup block inside `_larch_log_commit`, making future allowlist or git-status changes error-prone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `head_match` naming obscures merge-state comparison
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/merge.py` variable naming obscures stale-state versus updated-state comparison after force-push recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Breadcrumb writer is reallocated per breadcrumb
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/ship.py` creates a new `BreadcrumbWriter` for each breadcrumb call, adding minor allocation/noise in long loops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

