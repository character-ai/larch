# Review Round 3

- Mode: `diff`
- 9 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: clear-stall / seed contract vs split syntax–key guards
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-branching-output.txt
- **Severity**: important
- **Concern**: Documentation and contract text (`stall-recovery-report.md`) state that present but keyless or comment-only `ship-pr-state.sh` fails `check_ship_pr_state_format` and should `exit 3`. Implementation splits `check_ship_pr_state_syntax` (malformed lines → `exit 3`) from `ship_pr_state_has_keys` (keyless but syntax-valid → `clear-stall`: `CLEARED=false` / `exit 0`; `seed-terminal-state`: seed-fresh rewrite with `SEEDED=true`). Operators, doc-driven maintainers, or harnesses expecting `exit 3` for all non-absent “malformed” shapes mis-branch; after successful recovery an empty/keyless on-disk file can pair with terminal routing and seed re-asserting stall tracking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-branching-output.txt: Rewrite the two subcommand bullets to document the three-tier guard (symlink/non-regular → `exit 3`; syntax-invalid → `exit 3` + machine KV false; keyless-but-syntax-valid → clear: `CLEARED=false`/`exit 0`, seed: seed-fresh canonical rewrite/`SEED_MODE=seed`) and drop the claim that `check_ship_pr_state_format` alone drives `exit 3` for present files.
  - From cursor-specialist-edge-cases-output.txt: Widen clear to append keys on keyless files or branch step 7 so keyless files are not treated as terminal after success
  - From cursor-specialist-plan-fidelity-output.txt: After regular-file guard call check_ship_pr_state_format and exit 3 on failure; remove separate keyless exit-0 branch or update plan and harnesses


### FINDING_10: step-18b harness lacks real-helper integration
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-step-18b-final-report.sh` uses stub `write-final-report` and token-report only; production wrapper failures in rehydration, renderer coupling, or failure capture would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add at least one integration case invoking real step-18b-final-report.sh with real write-final-report.sh against a fixture tmpdir


### FINDING_12: classify fixtures for keyless on-disk vs session-env
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Classify now ignores zero-key `ship-pr-state.sh` and falls back to session-env with only one new test; partial on-disk state could classify differently than before extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add classify fixtures for comment-only/empty ship-pr-state.sh with conflicting session-env stall keys


### FINDING_13: implement-structure Step 18 pins omit STEP17_EMITTED_PRESENT / body guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Step 18 structural repin in `test-implement-structure.sh` omits `STEP17_EMITTED_PRESENT` parse and `-s summary-final.md` guard pins; future SKILL edits could drop parsed KVs or non-empty body guard while harness 16 still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend assertion 18 to require STEP17_EMITTED_PRESENT parsing and the -s summary-final.md prose guard


### FINDING_14: clear-stall success test omits BAIL_* key preservation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: clear-stall success case does not assert `BAIL_FAILURE_DETAIL_LOG` / `BAIL_REASON` preservation; a key-rewrite bug dropping canonical Step-8 keys might slip until implement-finalize/teardown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Augment the success fixture with BAIL_FAILURE_DETAIL_LOG and assert preservation after clear-stall


### FINDING_16: Step 18 cp-failure can force EMIT_BODY true (double emit)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In `step-18b-final-report.sh`, `cp` failure removes snapshot so `cmp` forces `EMIT_BODY=true` when step17-emitted present; transient `cp` failure after Step 17 emit could cause Step 18 double body emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)


### FINDING_4: clear-stall vs seed-terminal-state asymmetry on keyless present files
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Docs describe seed as sharing clear-stall malformed guards, but seed re-seeds keyless present files while clear no-ops (`CLEARED=false`, `exit 0`). Readers or harness authors may assume both subcommands reject the same present-file shapes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Clarify in stall-recovery.md that terminal seed may populate keyless present state
  - From cursor-specialist-correctness-output.txt: Document clear vs seed asymmetry for keyless present ship-pr-state.sh


### FINDING_6: Unsafe awk interpolation in rewrite_ship_pr_state_keys (seed path)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-awk-safety-output.txt
- **Severity**: latent
- **Concern**: `rewrite_ship_pr_state_keys` embeds values in awk source via string assembly. `cmd_clear_stall` uses fixed literals and is safe; `cmd_seed_terminal_state` can pass disk-backed `PHASE` / `STALL_STEP` from `kv_get` without `safe_phase_value` / `safe_step_value`, while syntax check allows metacharacters in values—crafted values could break out of awk string literals and execute arbitrary awk on rewrite (local code exec; requires tmpdir write access). Same pattern risks corrupting rewrites on quotes in operational values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use awk -v value assignments instead of string-built script
  - From cursor-specialist-security-output.txt: Re-apply safe_step_value/safe_phase_value after kv_get, or pass values with awk -v; add a harness case with metacharacters in PHASE
  - From cursor-specialist-edge-cases-output.txt: Escape values or avoid inline awk string assembly for disk rewrites
  - From dyn-awk-safety-output.txt: Always normalize disk-backed values before embedding: `step=$(safe_step_value "$(kv_get "$state" STALL_STEP "8")")` and `phase=$(safe_phase_value "$(kv_get "$state" PHASE "ci-initial")")`, then apply CLI overrides; prefer refactoring `rewrite_ship_pr_state_keys` to pass updates via `awk -v` (as in `cmd_record_attempt` at `656-659`) or a dedicated escaper so values are never spliced into program text.


### FINDING_9: Step 18 harness still exercises retired inline orchestration
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-write-final-report.sh` Step 18 cases still test retired inline `_wfr_*` orchestration instead of `step-18b-final-report.sh`; `EMIT_BODY` / `WFR_RC` logic in the wrapper could regress while tests pass via the removed SKILL.md path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Repoint Step 18 cases through step-18b-final-report.sh and assert EMIT_BODY/WFR_RC; restrict --print-stdout assertions to Step 17


