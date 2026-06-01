### FINDING_14: stall-recovery.md structure pins do not require helper delegation
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Structural tests can pass if Steps 7–8 revert from `stall-recovery-report.sh clear-stall` / `seed-terminal-state` to manual state-file edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Grep -Fq for clear-stall and seed-terminal-state invocations in stall-recovery.md
  - From dyn-harness-wiring-output.txt: Add `grep -Fq 'stall-recovery-report.sh clear-stall'` and `grep -Fq 'stall-recovery-report.sh seed-terminal-state'` (or equivalent literal pins) next to the existing terminal-shape pins in `scripts/test-implement-structure.sh`.


### FINDING_15: seed-fresh harness misses canonical EXIT_CODE/BAIL_REASON
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: nit
- **Concern**: Fresh seed tests do not assert `EXIT_CODE=4` and empty `BAIL_REASON=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert EXIT_CODE=4 and empty BAIL_REASON= on fresh seed output
  - From dyn-harness-wiring-output.txt: Assert `EXIT_CODE=4` via `read-session-env-key.sh` and `grep -q '^BAIL_REASON=$'` (or equivalent) on the seeded file in `case22-seed-fresh`.


### FINDING_16: WFR failure log not asserted
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The write-final-report failure path does not assert `step18-write-final-report.failure.log` exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert failure log exists in case-wfr-fail like token-report case


### FINDING_22: PLUGIN_ROOT stays stale after sourcing plugin-root.env
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-shell-state-output.txt
- **Severity**: important
- **Concern**: `step-18b-final-report.sh` sources `plugin-root.env` but does not refresh `PLUGIN_ROOT`, so standalone or mis-invoked runs can call helpers from the wrong plugin tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After sourcing plugin-root.env, set PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}" before helper calls (mirror step-7a.sh).
  - From dyn-shell-state-output.txt: After sourcing `plugin-root.env`, set `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}"` (or drop the redundant source and require callers to export `CLAUDE_PLUGIN_ROOT`, matching other implement helpers).


### FINDING_23: Empty ship-pr-state.sh passes format check
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A zero-byte `ship-pr-state.sh` can pass validation and be rewritten into a state missing canonical keys needed by downstream classify/rename gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Treat empty state as malformed (CLEARED=false exit 3) or require minimum canonical keys before rewrite.


### FINDING_25: SKILL prose still references old Step 18 dual-condition guard
- **Reviewer(s)**: dyn-emit-boundary-output.txt
- **Severity**: latent
- **Concern**: Step 18 bridge/NEVER prose still describes the old dual-condition guard instead of the authoritative wrapper `EMIT_BODY` / `WFR_RC` / non-empty-summary contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-emit-boundary-output.txt: Rewrite line 1363 to name the machine contract explicitly (parse `EMIT_BODY` / `WFR_RC` from `step-18b-final-report.sh`; emit only when `EMIT_BODY=true`, `WFR_RC=0`, and `summary-final.md` is non-empty), and drop “Step 17 did not print” / snapshot wording in favor of a pointer to Step 18b prose.
  - From dyn-emit-boundary-output.txt: Update the NEVER #20 “How to apply” tail to say Step 18 verbatim emission is allowed only when `EMIT_BODY=true` from `step-18b-final-report.sh` (plus the existing `WFR_RC=0` and non-empty `summary-final.md` checks in Step 18b), and retain the prompt-side `.step17-emitted` write-after-emit rule.


### FINDING_26: Structure test does not require WFR_RC capture
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `test-implement-structure.sh` pins `EMIT_BODY` parsing and `WFR_RC=0` prose, but not actual `WFR_RC=$(printf …)` capture from wrapper stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Extend the Step 18 awk (or a `grep -Fq`) to require `WFR_RC=$(printf` (and optionally `STEP17_EMITTED_PRESENT=$(printf`) alongside `EMIT_BODY=$(printf`, mirroring the existing `EMIT_BODY` pin.


### FINDING_5: clear-stall symlink rejection lacks harness coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: important
- **Concern**: `clear-stall` symlink rejection is not tested, while `seed-terminal-state` symlink rejection is covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add case22-clear-symlink expecting CLEARED=false and exit 3.
  - From cursor-specialist-testing-output.txt: Add case22-clear-symlink expecting exit 3 and CLEARED=false
  - From dyn-harness-wiring-output.txt: Add a `case22-clear-symlink` block mirroring `case22-seed-symlink` (symlinked `ship-pr-state.sh` → expect `CLEARED=false` and exit 3).


### FINDING_6: seed-terminal-state rewrite test misses preserved keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The rewrite-path test does not assert `EXIT_CODE` and `BAIL_REASON` survive rewrite.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Assert EXIT_CODE and BAIL_REASON unchanged after rewrite.


