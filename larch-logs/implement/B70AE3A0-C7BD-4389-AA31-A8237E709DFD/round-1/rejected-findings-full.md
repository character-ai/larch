### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Merge convergence acceptance lacks end-to-end single-CI-cycle test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Existing tests mainly assert no pre-merge `flush_logs_pre`; they do not prove the clean green ship path completes with one CI/monitor cycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: ship.py lacks executable Python 3.11 runtime guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-runtime-compat-output.txt
- **Severity**: latent
- **Concern**: The Python 3.11 floor is documented but not enforced at `ship.py` entry, so direct invocation under older interpreters can fail opaquely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-runtime-compat-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Stream/breadcrumb coverage mocks the behavior it should prove
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-stream-contract-output.txt
- **Severity**: important
- **Concern**: Tests manually call or isolate breadcrumb/output helpers instead of exercising real `main()`/`run_ship()` phase emission and stdout/stderr separation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-stream-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: implement skill lacks mechanical Python-path version fence
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-runtime-compat-output.txt
- **Severity**: important
- **Concern**: The Step 8+ skill fence still relies on prose/orchestrator discipline rather than a bash-enforced Python 3.11 probe and Python driver branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-runtime-compat-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Volatile-only tests target private helper instead of public flush integration
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests exercise `_larch_log_commit` directly rather than `flush_logs_pre` publish/classify/restore paths, leaving integration regressions possible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: CI poll breadcrumb test omits elapsed-time assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The CI poll breadcrumb test does not assert elapsed-seconds formatting from the injected clock.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Rebase loop can still flush logs and retrigger CI churn
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Although `merge_pr` no longer pre-flushes, the open-PR CI rebase loop still calls `flush_logs_pre` on each `goto_rebase`, risking repeated run-log commits and CI retriggers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Conflict URL recovery assumes recovered PR is open
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_recover_pr_from_conflict_text` hardcodes state `OPEN`, so closed or merged PR URLs could be treated as mergeable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: OID polling does not verify non-empty OID or remote ref agreement
- **Reviewer(s)**: dyn-merge-head-sync-output.txt
- **Severity**: latent
- **Concern**: `_poll_head_oid_match` treats `headRefOid == local_head` as sufficient without rejecting empty OIDs or comparing the remote tracking ref.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-head-sync-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_37

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_37: Volatile cleanup can stall on AM tracked sidecars
- **Reviewer(s)**: dyn-runlog-porcelain-output.txt
- **Severity**: important
- **Concern**: Cleanup decides restore targets from pre-reset porcelain and skips `A` rows; an `AM` tracked refresh sidecar can remain worktree-modified after reset, causing a fail-closed dirty-porcelain stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-porcelain-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: PR resolution logic is duplicated across create paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Post-create and conflict-recovery PR resolution duplicate similar URL/list-lag logic, increasing the chance future fixes land in only one path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_42

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_42: Success-path PR URL fallback is not scoped to the expected repo
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_recover_pr_from_conflict_text` can take the last pull URL from success stdout without verifying the repo slug, so a lagging `pr_for_branch` plus extra URLs could resolve the wrong PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: OID polling reuses merge-state retry constant
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `MERGE_PR_POST_PUSH_UNKNOWN_RETRIES` is reused for OID polling, making retry tuning misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Volatile-only helper adds thin indirection
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_volatile_only_under_run_tree` is a thin wrapper that adds indirection in an already large module.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

