### FINDING_1: Finalize-step5 still binds abort/success parsing to task-notification stdout
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The Step 5 finalize contract still teaches abort/success handling to read `FINAL_SUMMARY_PATH` from completed task-notification stdout, so the migrated Step 5c path can miss the summary source and skip required final-summary emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/design/references/finalize-step5.md. Replace task-notification stdout bindings with bgjob DONE result-env or captured bgjob wait stdout, aligned with the updated final-summary-emit.md profile.
  - From Codex-Arch: Add this file to UPDATED and rewrite the Step 5c / 5d contract around bgjob start, bgjob wait, result envs, and terminal-sentinel precedence.
  - From Codex-Innovation: Update this file to read the bgjob result env or the new shared bgjob-wait contract instead of task-notification stdout
  - From Cursor-Requirements: Add ### UPDATED: skills/design/references/finalize-step5.md: rebind abort and success parsing to bgjob wait DONE output and/or $TMPDIR/bgjob/design-step5c.result.env via design read-result-env; remove task-notification wording


### FINDING_3: bgjob wait does not gate DONE on BGJOB_RC
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The shared bgjob wait contract treats `BGJOB_STATUS=DONE` as normal continuation without checking `BGJOB_RC`, so timeout/orphaned results could be mistaken for successful completion instead of failure or stall routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In skills/shared/bgjob-wait.md require that DONE with BGJOB_RC in {timeout, orphaned} or missing required step KVs routes through the step existing failure or stall handling, not normal continuation. Pin the rule in scripts/test-implement-structure.sh or scripts/test-design-structure.sh.
  - From Cursor-Requirements: In bgjob-wait.md require parsing BGJOB_RC on DONE and routing timeout/orphaned/non-zero values through each step's existing failure or stall path; mirror in python/tests/bgjob/test_wait.py and prompt-shape harnesses


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


