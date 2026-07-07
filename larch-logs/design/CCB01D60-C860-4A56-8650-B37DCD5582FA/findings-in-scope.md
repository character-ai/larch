### FINDING_1: Finalize-step5 still binds abort/success parsing to task-notification stdout
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The Step 5 finalize contract still teaches abort/success handling to read `FINAL_SUMMARY_PATH` from completed task-notification stdout, so the migrated Step 5c path can miss the summary source and skip required final-summary emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/design/references/finalize-step5.md. Replace task-notification stdout bindings with bgjob DONE result-env or captured bgjob wait stdout, aligned with the updated final-summary-emit.md profile.
  - From Codex-Arch: Add this file to UPDATED and rewrite the Step 5c / 5d contract around bgjob start, bgjob wait, result envs, and terminal-sentinel precedence.
  - From Codex-Innovation: Update this file to read the bgjob result env or the new shared bgjob-wait contract instead of task-notification stdout
  - From Cursor-Requirements: Add ### UPDATED: skills/design/references/finalize-step5.md: rebind abort and success parsing to bgjob wait DONE output and/or $TMPDIR/bgjob/design-step5c.result.env via design read-result-env; remove task-notification wording

### FINDING_2: Step 18 cleanup still uses the retired .bg-wait-active stall marker
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The Step 18 cleanup reference still describes the fifth stall layer with the old `.bg-wait-active` marker, but abandoned-checks detection is moving to identity-checked bgjob registry rows, so killed self-review legs can miss the intended retry path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/implement/references/step18-cleanup.md. Document the fifth derived signal as identity-checked dead bgjob registry rows for implement-step3-checks and implement-step5-self-review, not .bg-wait-active.
  - From Cursor-Requirements: Add ### UPDATED: skills/implement/references/step18-cleanup.md: replace the fifth-layer .bg-wait-active rule with identity-checked dead bgjob registry rows for implement-step3-checks and implement-step5-self-review, aligned with stall-recovery.md

### FINDING_3: bgjob wait does not gate DONE on BGJOB_RC
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The shared bgjob wait contract treats `BGJOB_STATUS=DONE` as normal continuation without checking `BGJOB_RC`, so timeout/orphaned results could be mistaken for successful completion instead of failure or stall routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In skills/shared/bgjob-wait.md require that DONE with BGJOB_RC in {timeout, orphaned} or missing required step KVs routes through the step existing failure or stall handling, not normal continuation. Pin the rule in scripts/test-implement-structure.sh or scripts/test-design-structure.sh.
  - From Cursor-Requirements: In bgjob-wait.md require parsing BGJOB_RC on DONE and routing timeout/orphaned/non-zero values through each step's existing failure or stall path; mirror in python/tests/bgjob/test_wait.py and prompt-shape harnesses

### FINDING_4: Registry identity and filename derivation are still underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The registry contract does not pin how run-id is derived or how registry paths are built, so the required `<run-id>-<step>.env` layout is not enforced and concurrent sessions can collide on the same step name.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In registry.py and cli.py pin registry filenames to <run-id>-<step>.env, derive run-id at start from session RUN_ID or an equivalent per-run id in tmpdir keepalive, and require wait/status/reap to match on both run-id and step. Add a collision test in python/tests/bgjob/test_registry.py.
  - From Cursor-Requirements: Pin run-id capture in bgjob start (required when registry row is written), include RUN_ID/LARCH_RUN_ID in registry model fields, and add pytest coverage for distinct run-id rows for the same step

### FINDING_5: Parallel research lanes need distinct bgjob STEP names
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The research-phase migration does not pin unique bgjob STEP slugs per lane, so concurrent research starts can share one registry row and corrupt lane ownership.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In research-phase.md and validation-phase.md assign one bgjob STEP per external lane, for example research-arch and research-edge, and require waiting each STEP independently per skills/shared/bgjob-wait.md.

### FINDING_6: Step 4 tail contract still teaches the retired background fence
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The loaded Step 4 tail contract still describes the orchestrator backgrounding the fence and arming `.bg-wait-active`, so the skill surface remains stale even if the shell wrapper changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the markdown contract to UPDATED and replace the Step 4 launch text with the shared bgjob wait contract.

### FINDING_7: step-8-ship.md still contains the legacy run_in_background relaunch contract
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: `step-8-ship.md` still describes the old relaunch path, so the new bg-wait lint will flag the untouched contract doc and block acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add `skills/implement/scripts/step-8-ship.md` to the migration set and replace the legacy relaunch wording with the shared bgjob start/wait contract

### FINDING_8: The plan points at the wrong Step 8 ship path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The migration plan targets a non-existent Step 8 ship reference path, so the actual shipped wrapper doc will be skipped during review and migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Retarget the plan entry to ### UPDATED: skills/implement/scripts/step-8-ship.md and keep references/ship-pr-exit-matrix.md and ship-pr-ci-fix.md as separate items
