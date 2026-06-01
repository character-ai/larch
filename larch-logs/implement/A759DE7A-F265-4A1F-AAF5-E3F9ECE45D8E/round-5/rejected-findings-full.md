### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: python/run_logs.py monolithic module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_logs.py` combines manifest handling, KV parsing, execution-issues NDJSON, token/timing rendering, transcript capture, tree copy, and path guards in one ~830-line module. Phase 7 driver wiring and future log fixes require navigating unrelated concerns in a single file; regression risk rises with every flush-boundary change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split into focused modules; keep flush entrypoints as thin orchestrators.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: code-quality: push remote always origin; plan/docs mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Plan mentions origin vs upstream fork-aware remotes, but `select_push_remote` always returns `origin` and `git.remotes` is unused. Misleading for contributors implementing fork push later; wrong remote if a future fork flow needs `upstream`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align comments/plan with create-pr.sh origin-only behavior or implement real selection.
  - From cursor-specialist-correctness-output.txt: Implement fork-aware remote selection or document create-pr.sh origin-only parity.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: risk-integration: admin_merged recovery test mocks _flush_recoverable
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test_merge_flush_recovery_success_emits_admin_merged` mocks `_flush_recoverable` to always True. Bugs in the four flush predicates may not be exercised on the admin_merged recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Use scripted git helpers instead of patching `_flush_recoverable`, or add a positive `_flush_recoverable` unit test first.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: architecture: pr_body coupled to run_logs via path_under_repo
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `pr_body` imports `path_under_repo` from `run_logs`, coupling PR composition to logging. Any refactor of `run_logs` risks breaking PR body path validation and violates layer boundaries expected elsewhere under `python/`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Move `path_under_repo` to a neutral shared module imported by both.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: risk-integration: merge_pr ignores flush_logs_pre skip and continues
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `merge_pr` ignores `flush_logs_pre` skip and continues merge. Missing `ctx.state_file` skips pre-push log commit; merge proceeds without flush commit on branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Hard Phase 7 precondition on state_file or block merge on non-merge-ok skip reasons.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: architecture: flush_logs_pre ignores subprocess failures
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `flush_logs_pre` shells out to multiple `.sh` helpers with ignored exit codes. Failed token-report, transcript capture, or larch-log commit may leave partial logs while merge continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize subprocess exit handling with fail-closed or explicit `RefreshSkip` reasons per step.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: code-quality: merge.py duplicated _post_flush / BEHIND handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Repeated `_post_flush` early-return blocks and duplicated BEHIND handling make it easy to miss post-flush on a new exit path during Phase 7 edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract `_return_after_post_flush` helper and consolidate BEHIND branches.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

