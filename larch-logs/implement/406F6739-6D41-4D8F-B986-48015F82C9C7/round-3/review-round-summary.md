# Review Round 3

- Mode: `diff`
- 10 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Dead `_allow` array and duplicated inner-env parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: At `skills/design/scripts/run-step3-review.sh:219-223`, a dead `_allow` array is declared but never used, suggesting an incomplete refactor toward `phase_driver_read_result_env`. Inner `.step3-plan-review-result.env` parsing duplicates the shared allowlist via inline `case` arms instead of calling `phase_driver_read_result_env`, so future allowlist edits can drift between `_allow`, the case statement, and the library helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: No harness for symlinked `plan-review/round-*` skip path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The symlinked `plan-review/round-*` skip path has no behavioral harness coverage. A malicious or stale symlinked round directory could remain while tests only grep warning strings for the plan-review root symlink case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Invalid round-cap / convergence-threshold through real loop untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Invalid `LARCH_DESIGN_*` values documented to yield panel-failed at Step 3 are only regression-locked on stub-loop paths, not when the driver invokes the real `plan-review-loop.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Stale “rollback handled above” wording in SKILL.md
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Orchestrator prose may still imply rollback lives in the SKILL fence though rollback moved to `run-step3-review.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: Plan-fidelity harness still greps SKILL.md for pins moved to driver
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh:194-197` still greps `SKILL.md` for `set +e` / `_plan_review_rc` pins retargeted to `run-step3-review.sh` in the plan; fail messages name the driver while assertions scan the orchestrator file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: HARD write-cursor failure exits 0 with rollback instead of plan’s exit 1 abort
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: On HARD `snapshot-plan-round.sh` write-cursor failure (`run-step3-review.sh:164-187`), the driver rolls back `review-round-count.txt`, sets `LOOP_STATUS=panel-failed`, writes result env, and exits 0. Pre-refactor inline Step 3 persisted the pending round and exited 1 without rollback. Re-entry with `plan-after-round-N.txt` present can leave count at N−1 and route through the panel-failed short-circuit instead of aborting the fence with a consumed slot at N. Plan edge-case acceptance called for preserving exit 1 on this path; parity with that handoff is undocumented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Orchestrator sources stale `.step3-review-result.env` when driver exits non-zero
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-orchestrator-bridge-contract-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md:856-884` sources `$DESIGN_TMPDIR/.step3-review-result.env` whenever the file exists, without gating on `_plan_review_rc`. On failed `run-step3-review.sh` (exit 2 for argv/config, or exit 1 if `phase_driver_write_result_env` refuses a symlink), the driver may not refresh the file, but the fence can still load a prior run’s `LOOP_STATUS` / cap KVs. Round 2 removed the old “any non-zero rc → force `panel-failed`” guard, so an exit-2 warning can print while branching on stale `LOOP_STATUS=complete` or `converged`. Driver exit 2 only warns and may still leave orchestrator on panel-failed semantics with possible round-count persistence without a panel run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-orchestrator-bridge-contract-output.txt: Gate sourcing on success only (`[[ "${_plan_review_rc:-0}" -eq 0 ]]` before reading the result env), or delete/rename the result env at the start of the fence / on non-zero rc; then fall through to stdout fallback and the existing empty-`LOOP_STATUS` → `panel-failed` path.


### FINDING_7: Unchecked `phase_driver_write_result_env` at terminal write
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Terminal `phase_driver_write_result_env` at `run-step3-review.sh:272-284` does not check return status. A symlinked `.step3-review-result.env` can abort the driver without `emit_kv` breadcrumbs, leaving the orchestrator to misroute via panel-failed or stale file state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: Driver stdout breadcrumbs omit `STEP3_REVIEW_ROUND_NUM` and `ROUND_NUM`
- **Reviewer(s)**: dyn-orchestrator-bridge-contract-output.txt
- **Severity**: important
- **Concern**: Terminal `emit_kv` breadcrumbs (`run-step3-review.sh:286-295`) omit `STEP3_REVIEW_ROUND_NUM` and `ROUND_NUM` even though both are written to `.step3-review-result.env` and the SKILL bridge allowlists them for stdout fallback. If the orchestrator refuses to source a symlinked result env but stdout still carries `LOOP_STATUS`, the bridge can branch with a stale in-session `ROUND_NUM` (e.g. MainAgent re-tally path using `plan-review/round-${ROUNDS_COMPLETED:-$ROUND_NUM}/findings-classification.tsv`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-bridge-contract-output.txt: Add `emit_kv STEP3_REVIEW_ROUND_NUM` and `emit_kv ROUND_NUM` alongside the other terminal breadcrumbs so stdout fallback matches the normalized result-env contract.


### FINDING_9: No harness for orchestrator handling of driver exit 2
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No test covers orchestrator behavior when `run-step3-review.sh` exits 2. Misconfigured argv may print only the configuration-error line while downstream prose assumes panel-failed semantics without an integration assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


