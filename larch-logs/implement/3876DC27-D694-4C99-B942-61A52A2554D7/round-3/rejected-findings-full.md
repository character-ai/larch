### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Re-tally SCOPE_ANCHOR_FILE refresh is prose-pinned only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Re-tally `SCOPE_ANCHOR_FILE` refresh is prose-pinned only, not behaviorally tested. Stale-anchor or missing-KV re-tally regressions in SKILL orchestration could slip past CI despite documentation pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a behavioral fence case with re-tally stub stdout for ok vs tally-error and dual env file assertions.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: recover_main_agent_scope_anchor downgrades MAV to panel-failed on anchor recovery failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `recover_main_agent_scope_anchor` downgrades MAV to `panel-failed` when staged anchor recovery fails. Transient invalid anchor (empty post-redaction, permissions) loses entire main-agent vote path and skips Gate B/Step 3.6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use a narrower error terminal with WARN; reserve panel-failed for infra failures.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: larch_scope_anchor_relay_allowed reads global status variables
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `larch_scope_anchor_relay_allowed` reads global `LOOP_STATUS`/`TALLY_PLAN_REVIEW_STATUS` instead of parameters. A new caller that sets status under different variable names or before globals are assigned could omit or mis-gate `SCOPE_ANCHOR_FILE` without compile-time failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pass tally_status and loop_status as explicit function arguments


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: test-check-scope-reduction-marker registered under test-harnesses-7 not test-harnesses-18
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-check-scope-reduction-marker` is registered under `test-harnesses-7`, not `test-harnesses-18` as the plan suggested. No functional failure; only shard placement differs from the plan example.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Optionally move the target to test-harnesses-18 for plan alignment, or leave as-is if shard-7 placement is intentional.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: validate_design_prompt_file reimplements scope-anchor path rules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_design_prompt_file` in `render-plan-review-prompt.sh` reimplements scope-anchor path rules already in `lib-scope-anchor-handoff.sh`. Validation limits (64KiB, under-tmpdir, non-symlink) can drift between `render-plan-review-prompt` and `render-assessor-prompt`/`run-step3-review`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use larch_scope_anchor_validate_design for --feature-file validation


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Inconsistent symlink/canonicalization policy for scope-anchor paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Inconsistent symlink/canonicalization policy between revise validation and `lib-scope-anchor-handoff` validators. A symlinked scope-anchor path accepted by one consumer and rejected by another breaks handoff on edge-case tmpdir layouts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Unify on lib-scope-anchor-handoff validation helpers with one documented symlink policy


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

