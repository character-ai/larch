### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Migrated bgjob steps still inherit notification recovery in orchestrator-never
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-plan-fidelity-auto, dyn-dyn-bgjob-docs
- **Severity**: major
- **Concern**: `skills/shared/orchestrator-never.md` still mixes live bgjob guidance with legacy `<task-notification>` recovery. NEVER #3–#5 keep active notification reads and sentinel probes for migrated `/design` and `/implement` steps even though the preamble says those paths should follow `bgjob-wait.md`, which can stall on notifications that never arrive or re-authorize compatibility sentinels on bgjob steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.
  - From dyn-dyn-bgjob-docs: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: FINAL_SUMMARY_PATH can be bound from stale DONE output
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `skills/shared/final-summary-emit.md` binds `FINAL_SUMMARY_PATH` from `DONE` stdout without requiring `BGJOB_RC=0` from the same capture, so a stale success can be reused after a later failed wait.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Marker-first final-summary wording is ambiguous about env rereads
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The marker-first profile in `skills/shared/final-summary-emit.md` and the design profile disagree on whether result-env rereads are allowed, which makes the env-validation contract ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Missing structure-test pins for new bgjob NEVER rules and Step 8 carve-out
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bgjob-docs
- **Severity**: minor
- **Concern**: The new bgjob NEVER rules and Step 8 handoff exception are not backed by structure-test pins, so the orchestrator prompt can drift without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-docs: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Lint allowlist cardinality is not enforced
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `python/larch/lint/lint_bg_wait_coverage.py` only rejects unallowlisted prose and does not enforce allowlist cardinality or the exact path set, so stale rows can survive cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: NEVER #5 still cross-references notification-era design waits during bgjob WAIT loops
- **Reviewer(s)**: dyn-dyn-bgjob-docs
- **Severity**: minor
- **Concern**: NEVER #5 still routes bgjob WAIT handling through `design-background-wait.md` and NEVER #3, which can pull orchestrators back toward notification-era semantics instead of repeating bgjob waits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-docs: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: design SKILL still requires a full legacy background-wait read in Final summary
- **Reviewer(s)**: dyn-dyn-bgjob-docs
- **Severity**: major
- **Concern**: `skills/design/SKILL.md` still requires a full read of `design-background-wait.md` in Final summary even though `final-summary-emit.md` now keys off bgjob `DONE`/result-env truth, so the live skill and shared contract drift apart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-docs: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

