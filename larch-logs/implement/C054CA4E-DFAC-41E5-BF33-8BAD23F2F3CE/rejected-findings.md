### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `plan_block_present` duplicates plan-block-read marker logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `plan_block_present` in `design-route.sh` duplicates marker logic from `plan-block-read.sh`. Fixes to malformed-marker handling in `plan-block-read.sh` may not reach design-route already-planned routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Share one helper or call `plan-block-read.sh` for body-file presence checks.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Dual large Step 0b handoff fences in orchestrator prose
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two large Step 3-style handoff fences in `SKILL.md` (route and init). KV allowlist or merge-loop changes require duplicate edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider a follow-up shared snippet/helper after allowlists stabilize.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Plan acceptance enums lag landed drivers
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Acceptance `ROUTE` and `INIT_STATUS` enums omit `cancel-pause-load`, `env-refresh-failed`, `rename-failed`. Future plan-fidelity passes may treat intentional review deltas as missing work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Refresh acceptance bullets to match `design-route.md` and landed drivers.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Collected route WARN/ERROR arrays never re-emitted
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `_route_warn_lines` and `_route_error_lines` are populated during merge but not consumed afterward; there is no pre-`ROUTE` loop to print stored lines. If `result-env` read is skipped (e.g. symlink refusal) and stdout capture is empty, pause-load WARN/ERROR may not appear before ROUTE branching despite the arrays holding them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a pre-case loop printing stored WARN/ERROR lines, or remove the unused arrays.
  - From cursor-specialist-correctness-output.txt: Add explicit post-merge re-emit loop over arrays before ROUTE case, or remove unused arrays.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Embedded newlines in result-env WARN/ERROR could forge ROUTE lines
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: WARN/ERROR from pause-load are written to `.design-route-result.env` without newline rejection; Step 0b parses line-by-line without `phase_driver_read_result_env` sanitization on that path. An embedded newline in a value could make the orchestrator treat a forged `ROUTE=` line as a separate record and mis-route. Current pause-load tokens are fixed and safe; risk is latent if values change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate all KV values for newline/CR before `phase_driver_write_result_env`; consider enforcing the same in `phase_driver_write_result_env` globally.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Duplicate `validate_plain_scalar` / `validate_repo` in both drivers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_plain_scalar` and `validate_repo` are duplicated in `design-init-runparams.sh` and `design-route.sh`. Future argv rule changes need two edits and can diverge silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor validators into `lib-phase-driver.sh` and source from both drivers.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

