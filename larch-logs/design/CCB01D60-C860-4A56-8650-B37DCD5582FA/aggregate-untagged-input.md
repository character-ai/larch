### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/finalize-step5.md:90
- **Concern**: Step 5 finalize reference still binds abort-path FINAL_SUMMARY_PATH parsing to completed task-notification stdout. Scenario: The plan migrates Step 5c to bgjob but omits finalize-step5.md even though SKILL.md still mandates loading it for _publish_rc abort, stdout fallback, and final-summary emit. Line 90 still names design-step5c.sh completed task-notification stdout as the source. After migration the orchestrator can miss FINAL_SUMMARY_PATH on publish-tail abort and skip the required Read-always final-summary emit.
- **Proposed resolution**: Add ### UPDATED: skills/design/references/finalize-step5.md. Replace task-notification stdout bindings with bgjob DONE result-env or captured bgjob wait stdout, aligned with the updated final-summary-emit.md profile.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/step18-cleanup.md:15
- **Concern**: Step 18 cleanup reference still documents the fifth stall layer as a dead-PID .bg-wait-active marker. Scenario: The plan retires abandoned-checks detection in python/larch/state/_tokens.py to bgjob registry inspection and updates stall-recovery.md, but step18-cleanup.md is not listed. SKILL.md still requires reading step18-cleanup.md at Step 18. Operators and the orchestrator will keep using the retired marker rule while Python classifies abandoned checks via bgjob rows, so killed Step 3 or Step 5 self-review legs may not enter checks-commit-route-retry.
- **Proposed resolution**: Add ### UPDATED: skills/implement/references/step18-cleanup.md. Document the fifth derived signal as identity-checked dead bgjob registry rows for implement-step3-checks and implement-step5-self-review, not .bg-wait-active.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/shared/bgjob-wait.md
- **Concern**: Shared bgjob wait contract does not route DONE results with non-success BGJOB_RC values. Scenario: The plan has daemons write BGJOB_RC=timeout and BGJOB_RC=orphaned into the result env, and bgjob wait returns BGJOB_STATUS=DONE when that file exists. Section 3 only says on DONE parse KVs and continue existing branch handling. An orchestrator can treat budget timeout or owner-death as successful step completion instead of the step failure or stall path.
- **Proposed resolution**: In skills/shared/bgjob-wait.md require that DONE with BGJOB_RC in {timeout, orphaned} or missing required step KVs routes through the step existing failure or stall handling, not normal continuation. Pin the rule in scripts/test-implement-structure.sh or scripts/test-design-structure.sh.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/bgjob/registry.py
- **Concern**: Registry identity is under-specified versus the issue normative run-id-step filename contract. Scenario: The issue requires ~/.cache/larch/daemons/<run-id>-<step>.env rows. The plan validates step and run-id slugs but does not pin how start derives run-id or how registry paths are built. Result files live under per-tmpdir bgjob/, while the registry is global. Two sessions that share a STEP name can overwrite one registry row and misroute wait, reap, deny-hook active-run detection, and stall recovery.
- **Proposed resolution**: In registry.py and cli.py pin registry filenames to <run-id>-<step>.env, derive run-id at start from session RUN_ID or an equivalent per-run id in tmpdir keepalive, and require wait/status/reap to match on both run-id and step. Add a collision test in python/tests/bgjob/test_registry.py.

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/research/references/research-phase.md
- **Concern**: Parallel research lanes lack pinned distinct bgjob STEP names. Scenario: The edge case says start each lane separately but the migration list does not assign unique STEP slugs per arch, edge, ext, and sec lane. Four concurrent starts in one turn with one shared STEP would share one global registry row and corrupt lane ownership.
- **Proposed resolution**: In research-phase.md and validation-phase.md assign one bgjob STEP per external lane, for example research-arch and research-edge, and require waiting each STEP independently per skills/shared/bgjob-wait.md.

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/finalize-step5.md:84-111
- **Concern**: Loaded Step 5c contract still teaches task-notification/stdout completion, but the plan never updates this file.. Scenario: After the bgjob migration, the finalize path can still ship the retired wait contract on the design runtime surface, so Step 5c callers may keep parsing notification-era stdout instead of result envs.
- **Proposed resolution**: Add this file to UPDATED and rewrite the Step 5c / 5d contract around bgjob start, bgjob wait, result envs, and terminal-sentinel precedence.

### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-tail.md:23-25
- **Concern**: Loaded Step 4 tail contract still says the orchestrator backgrounds the fence and arms `.bg-wait-active`, but the plan only updates the shell wrapper.. Scenario: The Step 4 debate tail will run with new code but stale contract text, so the skill surface still points at the retired background primitive for one of the named migration sites.
- **Proposed resolution**: Add the markdown contract to UPDATED and replace the Step 4 launch text with the shared bgjob wait contract.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ship.md:26
- **Concern**: `step-8-ship.md` still contains the old `run_in_background` Step 8 relaunch contract. Scenario: The new inverse `bg-wait-coverage` lint scans `skills/**/*.md`, so this untouched contract doc will trip the lint and block acceptance even if the code lands
- **Proposed resolution**: Add `skills/implement/scripts/step-8-ship.md` to the migration set and replace the legacy relaunch wording with the shared bgjob start/wait contract

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/finalize-step5.md:90
- **Concern**: `finalize-step5.md` still tells Step 5c abort handling to parse `FINAL_SUMMARY_PATH` from completed `<task-notification>` stdout. Scenario: The bgjob migration removes task-notification dependence, so the canonical Step 5c failure path would still point at a source that no longer exists and leave the abort branch unverifiable
- **Proposed resolution**: Update this file to read the bgjob result env or the new shared bgjob-wait contract instead of task-notification stdout

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/finalize-step5.md:90
- **Concern**: Mandatory Step 5 finalize reference still sources Step 5c abort FINAL_SUMMARY_PATH from completed task-notification stdout. Scenario: After Step 5c moves under bgjob, the wrapper emits only BGJOB_STATUS=STARTED; operators following finalize-step5.md on _publish_rc=2/5 abort will look for FINAL_SUMMARY_PATH in a surface that no longer exists and can skip required final-summary emission
- **Proposed resolution**: Add ### UPDATED: skills/design/references/finalize-step5.md: rebind abort and success parsing to bgjob wait DONE output and/or $TMPDIR/bgjob/design-step5c.result.env via design read-result-env; remove task-notification wording

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/step18-cleanup.md:15
- **Concern**: Mandatory Step 18 cleanup reference still treats dead .bg-wait-active as the fifth stall-tracking layer for checks legs. Scenario: Plan migrates abandoned-checks detection in python/larch/state/_tokens.py to bgjob registry rows, but Step 18 still instructs orchestrators to derive stall state from .bg-wait-active; killed Step 3/Step 5 self-review bgjobs can miss transient-infra retry after markers are retired
- **Proposed resolution**: Add ### UPDATED: skills/implement/references/step18-cleanup.md: replace the fifth-layer .bg-wait-active rule with identity-checked dead bgjob registry rows for implement-step3-checks and implement-step5-self-review, aligned with stall-recovery.md

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/cli.py
- **Concern**: Registry filename run-id source is unspecified despite global ~/.cache/larch/daemons/<run-id>-<step>.env normative layout. Scenario: Issue scope requires run-id plus step registry names; the plan defines slug validation and paths but never binds --run-id (from LARCH_RUN_ID/RUN_ID/session env) on bgjob start, so concurrent sessions can collide on the same step name and wait/reap can target the wrong daemon
- **Proposed resolution**: Pin run-id capture in bgjob start (required when registry row is written), include RUN_ID/LARCH_RUN_ID in registry model fields, and add pytest coverage for distinct run-id rows for the same step

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/shared/bgjob-wait.md
- **Concern**: Shared wait contract treats any DONE as continuation without normative BGJOB_RC gating. Scenario: Daemon budget and owner-death paths write result env with BGJOB_RC=timeout or BGJOB_RC=orphaned while bgjob wait still returns BGJOB_STATUS=DONE; orchestrators that only branch on DONE vs DEAD can advance Step 3/5/5c/8 as if the leg succeeded
- **Proposed resolution**: In bgjob-wait.md require parsing BGJOB_RC on DONE and routing timeout/orphaned/non-zero values through each step's existing failure or stall path; mirror in python/tests/bgjob/test_wait.py and prompt-shape harnesses

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/references/step-8-ship.md
- **Concern**: Plan lists a non-existent Step 8 ship reference path. Scenario: The live shipped wrapper contract is skills/implement/scripts/step-8-ship.md (with Edit-in-sync harness deps); listing skills/implement/references/step-8-ship.md will skip the doc operators and test-implement-structure actually use during Step 8 bgjob migration
- **Proposed resolution**: Retarget the plan entry to ### UPDATED: skills/implement/scripts/step-8-ship.md and keep references/ship-pr-exit-matrix.md and ship-pr-ci-fix.md as separate items
