### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` `scripts/ship-pr.sh:453`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/ship-pr.sh:453`      `run_checks_phase` does not re-run checks after the third `LINT_FIX_STATUS=applied`. Concrete scenario: attempts 1 and 2 apply partial fixes, attempt 3 applies the final fix, then `continue` exits the `for lint_attempt in 1 2 3` loop and line 478 records the stale pre-fix check failure, stalling even though the tree may now pass. Change the loop so every applied fix is followed by one verification run, while limiting the number of fix dispatches to 3.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## code-quality: scripts/test-implement-structure.sh:345-360

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] STALL_STEP=6 anti-Edit/Write awk requires forbidden phrases on the same line as STALL_STEP=6. Wrapped SKILL.md lines could bypass the guard while still suggesting forbidden orchestration. Use multiline awk paragraph mode or a simpler full-file negative grep with bounded context.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## code-quality: skills/implement/SKILL.md ~1687

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] PHASE=checks stall described as CI errors Readers may conflate local relevant-checks with GitHub CI when triaging Exit 4 STALL_STEP=6. Use wording like local checks or PHASE=checks / relevant-checks instead of CI errors.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## code-quality: skills/implement/SKILL.md:1687

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Exit 4 bullet calls checks-phase failures CI errors. Operator conflates local relevant-checks with GitHub CI and follows wrong runbook. Use precise wording (relevant-checks / PHASE=checks).
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## code-quality: skills/implement/SKILL.md:1687

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] STALL_STEP=6 prose says CI errors for PHASE=checks. Terminology mismatches actual local checks phase. Use relevant-checks or check failures wording.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## correctness: scripts/lint-fix-loop.md:3-4

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Opening contract paragraph omits ship-pr call site despite plan to list it. Operators reading only the intro still think lint-fix-loop is only for Steps 3/5/6. Add ship-pr run_checks_phase ship-pr-ci-initial to opening contract prose.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:427-479

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Third LINT_FIX_STATUS=applied iteration uses continue which exits the for loop without a follow-up run-relevant-checks-captured.sh. Checks fail on iterations 1-2; third external fix makes checks pass but tree is never re-verified before record_failure/exit_stall 6; or third fix would pass and run is stalled anyway. After third applied or restructure loop so every applied is always followed by a check run until pass or max attempts.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:427-479

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Third lint-fix applied iteration uses continue; for loop has no fourth iteration after third applied. After three apply cycles without an intervening green check, the phase never runs a final relevant-checks pass; a tree that would pass can still record_failure and exit_stall. After last allowed apply, unconditionally run checks once more, or replace for-loop with while+counter that runs a final check after the cap.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:427-480

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Third lint_attempt with LINT_FIX_STATUS=applied skips a final check run Three failing check rounds then a successful third external fix stalls without re-running run-relevant-checks-captured.sh; false STALL_STEP=6. After the third applied (or on last loop iteration) run checks once more before stalling; or restructure loop so applied always pairs with a check run.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `risk-integration` `scripts/ship-pr.sh:873`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/ship-pr.sh:873`      The requested CI failure path was not wired into `run_ci_phase`: `evaluate_failure` still goes through `run_ci_fix_vendor`, and local post-fix check failures at `scripts/ship-pr.sh:805-810` never call `lint-fix-loop.sh` or parse `LINT_FIX_STATUS`. Concrete scenario: `ci-wait.sh` emits `ACTION=evaluate_failure` during `ci-merge`; the script launches the old CI fix helper, then on failing local checks retries that helper three times and stalls, instead of using `lint-fix-loop.sh --site ship-pr-ci-merge` and falling back only when `LINT_FIX_STATUS=failed`. Add both `ship-pr-ci-initial` and `ship-pr-ci-merge` labels to `lint-fix-loop.sh`, and route the `run_ci_phase`/`run_evaluate_failure` local check failure logs through `lint-fix-loop.sh` as described by the feature.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:430-479

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Third lint_attempt with LINT_FIX_STATUS=applied uses continue, ending the for loop without another check run. Checks fail three times; each lint-fix applies a real fix; the third fix makes checks passable on the next run; script stalls with STALL_STEP=6 instead of advancing to bump. After applied on attempt 3, run run-relevant-checks-captured once more before stalling, or restructure the loop so applied always implies a subsequent check.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:452-477

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Third lint_attempt with LINT_FIX_STATUS=applied uses continue but no further for-iteration reruns checks. After three failing check runs each followed by applied fixes the function never runs checks again before record_failure exit_stall 6; can false-stall if the last fix would pass checks and misattributes rc from the iteration-3 pre-fix check. On applied when lint_attempt is 3 run run-relevant-checks-captured once more before stalling or replace continue with explicit terminal re-check.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## risk-integration: scripts/lint-fix-loop.md:41-42

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Intro still lists only Steps 3/5/6 as consumers. Readers miss that ship-pr can invoke the helper. Add ship-pr checks phase to the opening contract sentence.
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## risk-integration: scripts/test-implement-structure.sh:354-360 skills/implement/SKILL.md:1687

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] STALL_STEP=6 awk guard matches Edit.*Write on the same line as the new MUST NOT Edit/Write sentence. scripts/test-implement-structure.sh fails awk gate while SKILL.md matches intended policy. Narrow regex split lines or rephrase without Edit/Write substring on STALL_STEP=6 line.
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## risk-integration: scripts/test-implement-structure.sh:355-360

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] STALL_STEP=6 vs forbidden prose must share one line for awk match. Markdown reflow removes the guard without failing tests. Use multi-line awk or separate greps.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## architecture: feature_description vs branch

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Dual requirements: feature_description lists ship-pr-ci-merge; diff only adds ship-pr-ci-initial. If issue text is authoritative merge-site labeling and merge-phase dispatch are missing. Reconcile scope: implement merge site or amend feature text to match plan.
- **Suggested revision**: Address the concern above.

