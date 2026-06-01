### FINDING_1: Post-mv destination STALL_TRACKING re-read can emit false success
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-kv-emission-atomicity-output.txt
- **Severity**: important
- **Concern**: After `mv`, `clear-stall` and `seed-terminal-state` re-read `STALL_TRACKING` on the destination `ship-pr-state.sh` using `if tracking=$(read-session-env-key.sh ...); then ...` instead of the temp-read `|| emit_cleared_false_exit` / `|| emit_seeded_false_exit` chain. On non-zero read exit, the `if` branch is skipped, value checks are skipped, and the scripts can still emit `CLEARED=true` or `SEEDED=true` without proving disk state—breaking the documented contract and risking orchestrator in-memory stall clear while disk still has `STALL_TRACKING=true` (or unverified seed).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-kv-emission-atomicity-output.txt: Mirror the temp-read chain: `tracking=$(read-session-env-key.sh --file "$state" ...) || emit_cleared_false_exit 1` (and the seed analogue), then `if [ "$tracking" != false ]` / `!= true`; remove the outer `if ...; then` wrapper. Add harness cases that stub `read-session-env-key.sh` to exit 1 on the destination call only (distinct from `noop-mv`, which exercises a stale/wrong value with exit 0).


### FINDING_11: Harness gap: temp read wrong value after rewrite
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Plan requires temp-read assert failure to emit `CLEARED=false`; tests cover mktemp/mv/dest value but not wrong value on temp after rewrite—a bug leaving `STALL_TRACKING=true` in temp could pass temp write and only fail open at destination depending on `mv` outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Only first step-18b case asserts `.step17-emitted` never written
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Only the first harness case asserts the wrapper never writes `.step17-emitted`; a later case could regress to writing the sentinel without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: clear-stall test does not assert PR_URL preservation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: clear-stall append case sets `PR_URL` but does not assert preservation after rewrite; regression dropping `PR_*` keys on clear would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: STEP17_EMITTED_PRESENT parsed but unused in orchestrator prose
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `STEP17_EMITTED_PRESENT` is parsed but unused; dead parse line and possible divergence between structural pin and runtime emit logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: step-18b snapshot cp failure can force duplicate EMIT_BODY emit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Snapshot `cp` failure removes `.step18-prebody` and can force `EMIT_BODY=true` even when `.step17-emitted` exists and `summary-final.md` is unchanged after `write-final-report`, causing a second verbatim emit (NEVER #20 duplicate). On `cp` failure with `.step17-emitted` present, require `cmp` proof of change before promoting `emit_body`; do not treat absent prebody alone as changed when the sentinel is set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: test-step-18b-final-report omitted from Makefile mega .PHONY line
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-step-18b-final-report` omitted from mega aggregate `.PHONY` line 4 per plan literal wording; inconsistent with `test-write-final-report` registration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add test-step-18b-final-report to line 4 mega .PHONY or amend plan to match dedicated-line convention


### FINDING_30: Bash 3.2 compound `local -a keys=() vals=() awk_v=()` in rewrite helper
- **Reviewer(s)**: dyn-bash32-array-compat-output.txt
- **Severity**: latent
- **Concern**: GNU Bash 3.2 only applies array attributes to the first name in a multi-variable `local -a` declaration; `vals` and `awk_v` start as empty scalars and rely on implicit promotion on `+=`—a portability footgun on the stall-state rewrite path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-array-compat-output.txt: Split into three declarations on separate lines (`local -a keys=()` / `local -a vals=()` / `local -a awk_v=()`), matching `BASH_AUTHORING.md` §3 style; optionally harden the final call with the repo’s Bash 3.2 empty-array idiom `"${awk_v[@]+"${awk_v[@]}"}"` (see `scripts/test-render-final-summary-bash32.sh` / issue #3039) if `n` can ever be zero.


### FINDING_9: Contract documents `snapshot_ok` but script does not emit it
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `step-18b-final-report.md` documents `snapshot_ok` but `step-18b-final-report.sh` has no such variable or KV; maintainers/operators may expect a machine-readable snapshot status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Remove snapshot_ok from the contract or add the variable to the script


