Normalizing the supplied reviewer findings into a merged structured list (read-only; no file writes).
Structured aggregator output (plain text for `aggregator-output.txt`):

### FINDING_1: Dead `_allow` array and duplicated inner-env parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: At `skills/design/scripts/run-step3-review.sh:219-223`, a dead `_allow` array is declared but never used, suggesting an incomplete refactor toward `phase_driver_read_result_env`. Inner `.step3-plan-review-result.env` parsing duplicates the shared allowlist via inline `case` arms instead of calling `phase_driver_read_result_env`, so future allowlist edits can drift between `_allow`, the case statement, and the library helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_4: Missing normalized result env treated as panel-failed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `.step3-review-result.env` is absent (driver `set -e` abort, symlink refusal on write, or other paths that skip a terminal write), the orchestrator falls back to empty `LOOP_STATUS` and then `panel-failed`, effectively degrading instead of failing closed. The driver should emit terminal `LOOP_STATUS` on all error paths, or the fence should fail closed when normalized result env is missing after a failed run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Orchestrator no longer validates `LOOP_STATUS` against closed enum after loading result env
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: After reading `.step3-review-result.env`, `skills/design/SKILL.md:856-884` no longer checks `LOOP_STATUS` against the closed enum. Same-UID tampering of the result env between driver exit and orchestrator read can spoof `LOOP_STATUS` and mis-route Gate B / Step 3 short-circuits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: Harness-only script path overrides lack production guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH` and `RUN_STEP3_PLAN_REVIEW_LOOP_SH` (`run-step3-review.sh:154-155,193-194`) redirect production script paths without a harness-only guard. Session env poisoning could make Step 3 execute attacker-chosen binaries with session privileges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

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

### FINDING_12: Duplicated scenarios across Step 3 harnesses
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Overlapping scenarios in `test-run-step3-review.sh` and `test-step3-review-cap.sh` increase maintenance drift risk; a fix in one harness may leave the other stale until CI fails on the other target.
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

### FINDING_15: [OUT_OF_SCOPE] Step 3.6 does not consume driver-persisted `ROUND_NUM`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Step 3.6 re-reads `ROUND_CURSOR` from `snapshot-plan-round.sh` instead of sourcing `ROUND_NUM` from `.step3-review-result.env` written by the new driver. Cross-fence shell locals were already unreliable; the driver persists `ROUND_NUM` but Step 3.6 does not consume it (pre-existing gap).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] `phase_driver_read_result_env` exported but unused by first consumer
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-orchestrator-bridge-contract-output.txt
- **Severity**: nit
- **Concern**: `lib-phase-driver.sh:59-77` defines `phase_driver_read_result_env` (tested) but `run-step3-review.sh` still uses inline `case` parsing and a dead `_allow` array. Future drivers may copy the inline pattern and diverge from the shared primitive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-orchestrator-bridge-contract-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] `test-lib-phase-driver.sh` uses `TMPDIR` not larch sessions cache
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-lib-phase-driver.sh` uses `TMPDIR` instead of the `~/.cache/larch/sessions` convention used by sibling harnesses, diverging from repo session tmp roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Newline-bearing KV values can expand result-env lines
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Newline-bearing KV values can produce extra result-env lines when persisted; spoofed inner env can set multiple orchestrator variables via one logical value (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] `--design-tmpdir` not rooted under larch session directory
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--design-tmpdir` is not validated as rooted under a larch session directory; a malicious or mistaken argument can enable read/write outside intended session artifacts (pre-existing trust model).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] `approval-gates.md` dual result-env references out of sync
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-orchestrator-bridge-contract-output.txt
- **Severity**: latent
- **Concern**: Gate B instructions still normatively reference `.step3-plan-review-result.env` while the Step 3 branch matrix cites normalized `.step3-review-result.env`. Both can exist after a successful run; doc drift risks inconsistent handoff guidance, not a missing bridge key for gate dispatch in this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-orchestrator-bridge-contract-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] SIMPLE tier cap vs `LARCH_DESIGN_ROUND_CAP` can disagree
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: SIMPLE tier may hit review-round cap at 3 while the loop uses env round-cap 5; tier cap and `LARCH_DESIGN_ROUND_CAP` can disagree (pre-existing policy).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Dropped inner keys not copied to normalized result env (intentional)
- **Reviewer(s)**: dyn-orchestrator-bridge-contract-output.txt
- **Severity**: latent
- **Concern**: The driver parses inner keys (`REASON`, `REVISE_STATUS`, `CONVERGENCE_STREAK`, `COLLECT_*`, `VOTER_1_PARSE_RATE_STATUS`) for loop handoff but does not copy them into `.step3-review-result.env`. This matches the documented normalized surface and is not a silent orchestrator regression: `SKILL.md` does not reference those shell variables after the bridge; Gate B reads inner/`round-summary.env` paths directly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-bridge-contract-output.txt: Address the concern above.

---

**Merge notes (for voters, not machine output):**

- Input **FINDING_29** (allowlist parity confirmation) and **FINDING_32** (branch commit list) were treated as non-actionable attestations and omitted.
- **FINDING_7** (exit-2 test gap) was kept separate from **FINDING_3** (orchestrator stale-env behavior) because fixes differ (harness vs fence gating).
- **FINDING_30** was subsumed into **FINDING_1** (in-scope) and **FINDING_16** (OOS unused-helper angle).
