### FINDING_1: clear-stall / seed contract vs split syntax–key guards
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-branching-output.txt
- **Severity**: important
- **Concern**: Documentation and contract text (`stall-recovery-report.md`) state that present but keyless or comment-only `ship-pr-state.sh` fails `check_ship_pr_state_format` and should `exit 3`. Implementation splits `check_ship_pr_state_syntax` (malformed lines → `exit 3`) from `ship_pr_state_has_keys` (keyless but syntax-valid → `clear-stall`: `CLEARED=false` / `exit 0`; `seed-terminal-state`: seed-fresh rewrite with `SEEDED=true`). Operators, doc-driven maintainers, or harnesses expecting `exit 3` for all non-absent “malformed” shapes mis-branch; after successful recovery an empty/keyless on-disk file can pair with terminal routing and seed re-asserting stall tracking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-branching-output.txt: Rewrite the two subcommand bullets to document the three-tier guard (symlink/non-regular → `exit 3`; syntax-invalid → `exit 3` + machine KV false; keyless-but-syntax-valid → clear: `CLEARED=false`/`exit 0`, seed: seed-fresh canonical rewrite/`SEED_MODE=seed`) and drop the claim that `check_ship_pr_state_format` alone drives `exit 3` for present files.
  - From cursor-specialist-edge-cases-output.txt: Widen clear to append keys on keyless files or branch step 7 so keyless files are not treated as terminal after success
  - From cursor-specialist-plan-fidelity-output.txt: After regular-file guard call check_ship_pr_state_format and exit 3 on failure; remove separate keyless exit-0 branch or update plan and harnesses

### FINDING_2: Duplicate malformed-line scan in state helpers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `check_ship_pr_state_syntax` and `ship_pr_state_has_keys` duplicate malformed-line scanning; future format-rule changes may be updated in one function and forgotten in the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)

### FINDING_3: Duplicated atomic temp-write / mv commit chain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `clear-stall` and `seed-terminal-state` duplicate the temp-write, read-assert, mv, dest-assert chain; bugfixes to atomic commit semantics must be applied twice.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)

### FINDING_4: clear-stall vs seed-terminal-state asymmetry on keyless present files
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Docs describe seed as sharing clear-stall malformed guards, but seed re-seeds keyless present files while clear no-ops (`CLEARED=false`, `exit 0`). Readers or harness authors may assume both subcommands reject the same present-file shapes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Clarify in stall-recovery.md that terminal seed may populate keyless present state
  - From cursor-specialist-correctness-output.txt: Document clear vs seed asymmetry for keyless present ship-pr-state.sh

### FINDING_5: STEP17_EMITTED_PRESENT parsed but unused in Step 18 prose
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `STEP17_EMITTED_PRESENT` is parsed in Step 18 orchestrator/SKILL prose but not used for branching; adds KV noise and may be mistaken as a required gate when `EMIT_BODY` already encodes emit gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove parse or document required orchestrator use
  - From cursor-specialist-correctness-output.txt: Remove parse or document as diagnostic-only
  - From cursor-specialist-plan-fidelity-output.txt: Mark informational-only in step-18b-final-report.md or reference once in Step 18b diagnostic prose

### FINDING_6: Unsafe awk interpolation in rewrite_ship_pr_state_keys (seed path)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-awk-safety-output.txt
- **Severity**: latent
- **Concern**: `rewrite_ship_pr_state_keys` embeds values in awk source via string assembly. `cmd_clear_stall` uses fixed literals and is safe; `cmd_seed_terminal_state` can pass disk-backed `PHASE` / `STALL_STEP` from `kv_get` without `safe_phase_value` / `safe_step_value`, while syntax check allows metacharacters in values—crafted values could break out of awk string literals and execute arbitrary awk on rewrite (local code exec; requires tmpdir write access). Same pattern risks corrupting rewrites on quotes in operational values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use awk -v value assignments instead of string-built script
  - From cursor-specialist-security-output.txt: Re-apply safe_step_value/safe_phase_value after kv_get, or pass values with awk -v; add a harness case with metacharacters in PHASE
  - From cursor-specialist-edge-cases-output.txt: Escape values or avoid inline awk string assembly for disk rewrites
  - From dyn-awk-safety-output.txt: Always normalize disk-backed values before embedding: `step=$(safe_step_value "$(kv_get "$state" STALL_STEP "8")")` and `phase=$(safe_phase_value "$(kv_get "$state" PHASE "ci-initial")")`, then apply CLI overrides; prefer refactoring `rewrite_ship_pr_state_keys` to pass updates via `awk -v` (as in `cmd_record_attempt` at `656-659`) or a dedicated escaper so values are never spliced into program text.

### FINDING_7: stall-recovery-report.sh growth / modularization
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Roughly 250 LOC added to an already large multi-purpose script; harder reviews and higher cross-subcommand regression risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)

### FINDING_8: Post-recovery orchestration when on-disk state is keyless
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `validate_ship_pr_state` is syntax-only; `clear-stall` refuses keyless present state while classify may still use session/in-memory layers. After recovery success with truncated empty `ship-pr-state.sh`, `clear-stall` returns `CLEARED=false` `exit 0` while orchestrator may still route to terminal despite recovery completion.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)

### FINDING_9: Step 18 harness still exercises retired inline orchestration
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-write-final-report.sh` Step 18 cases still test retired inline `_wfr_*` orchestration instead of `step-18b-final-report.sh`; `EMIT_BODY` / `WFR_RC` logic in the wrapper could regress while tests pass via the removed SKILL.md path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Repoint Step 18 cases through step-18b-final-report.sh and assert EMIT_BODY/WFR_RC; restrict --print-stdout assertions to Step 17

### FINDING_10: step-18b harness lacks real-helper integration
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-step-18b-final-report.sh` uses stub `write-final-report` and token-report only; production wrapper failures in rehydration, renderer coupling, or failure capture would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add at least one integration case invoking real step-18b-final-report.sh with real write-final-report.sh against a fixture tmpdir

### FINDING_11: Step 18 --print-stdout removal under-tested end-to-end
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Step 18 drops `write-final-report --print-stdout`; summary body is orchestrator-only when `EMIT_BODY=true`. Collapsible Bash output no longer shows the body (operators may think render failed); documented delta is not fully exercised against real renderer parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Keep documented intentional delta; no code change required
  - From cursor-specialist-testing-output.txt: Add a case asserting summary-final.md parity with/without --print-stdout and that the wrapper never prints the body

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

### FINDING_15: case-plugin-root-fallback does not hit wrapper-internal plugin-root path
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: latent
- **Concern**: `case-plugin-root-fallback` pre-sources `plugin-root.env` before invoking the wrapper, so `CLAUDE_PLUGIN_ROOT` is already set and the internal `if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$tmpdir/plugin-root.env" ]` branch in `step-18b-final-report.sh` is never exercised; documented wrapper-only contract is unverified though production pre-sources via orchestrator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-fidelity-output.txt: Add a case that invokes `"$impl_dir/step-18b-final-report.sh"` with `env -u CLAUDE_PLUGIN_ROOT` and only `$tmpdir/plugin-root.env` present (no `set -a` pre-source), asserting `EMIT_BODY=true` and stub helper usage; or narrow `step-18b-final-report.md:16` to state that plugin-root rehydration is orchestrator-owned and drop the unused internal branch if belt-and-suspenders coverage is not desired.

### FINDING_16: Step 18 cp-failure can force EMIT_BODY true (double emit)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In `step-18b-final-report.sh`, `cp` failure removes snapshot so `cmp` forces `EMIT_BODY=true` when step17-emitted present; transient `cp` failure after Step 17 emit could cause Step 18 double body emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)

### OOS_1: [OUT_OF_SCOPE] Pre-existing monolithic stall-recovery-report surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pre-existing monolithic classify/report/attempt surface amplified by this branch; not introduced by E1/E2 design choice alone—track as follow-up modularization.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)

### OOS_2: [OUT_OF_SCOPE] classify hard-exits on syntax error without classification KVs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Classify still hard-exits via `validate_ship_pr_state` on syntax errors without classification KVs; malformed line aborts classify with bare exit 3—pre-existing, not introduced by clear-stall/seed extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)

### OOS_3: [OUT_OF_SCOPE] Doc references check_ship_pr_state_format vs split helper exit matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Documentation references `check_ship_pr_state_format` but clear-stall/seed use split syntax/has_keys checks with different exit codes for zero-key files; documentation/implementation drift for edge-case exit semantics not exercised by current tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)

### OOS_4: [OUT_OF_SCOPE] Future caller could pass arbitrary keys into rewrite_ship_pr_state_keys
- **Reviewer(s)**: dyn-awk-safety-output.txt
- **Severity**: latent
- **Concern**: `rewrite_ship_pr_state_keys` accepts arbitrary caller-supplied key names; only current callers pass fixed names—no key allowlist or escaping, so a future caller could introduce key-side awk injection. Hardening (allowlisted keys + `awk -v`) would close the footgun; not introduced by a bad caller in this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)

### OOS_5: [OUT_OF_SCOPE] E2 step-18b has no awk usage for this safety pass
- **Reviewer(s)**: dyn-awk-safety-output.txt
- **Severity**: nit
- **Concern**: Branch adds no awk usage in `step-18b-final-report.sh`; E2 is out of scope for this awk-safety pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)

### OOS_6: [OUT_OF_SCOPE] Branch commit inventory (dyn-awk meta)
- **Reviewer(s)**: dyn-awk-safety-output.txt
- **Severity**: nit
- **Concern**: Commits on branch since `main` listed for context (`4d3623378` extract, `828ae39de` larch-logs, review/relevant-checks rounds, etc.)—informational only.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)

### OOS_7: [OUT_OF_SCOPE] cmd_seed_terminal_state lifecycle scout (no defect)
- **Reviewer(s)**: dyn-state-branching-output.txt
- **Severity**: nit
- **Concern**: Scout attestation: empty/comment-only seed path, `tmp` guard, and failure paths emit promised `SEEDED=false` KVs—no unreachable path or bare `set -e` skip identified.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)

### OOS_8: [OUT_OF_SCOPE] STEP17_EMITTED_PRESENT informational-only (scout)
- **Reviewer(s)**: dyn-state-branching-output.txt
- **Severity**: nit
- **Concern**: Parsed in SKILL.md but unused; emit gating fully in `EMIT_BODY`—informational-only, not a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)

### OOS_9: [OUT_OF_SCOPE] Orphan temp files on mv failure (acceptable)
- **Reviewer(s)**: dyn-state-branching-output.txt
- **Severity**: nit
- **Concern**: On `mv` failure or noop-mv dest-assert failure, orphan `ship-pr-state.sh.tmp.*` may remain; on-disk state unchanged and KVs correct per harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)

### OOS_10: [OUT_OF_SCOPE] Intentional plan deltas (classify empty state, Step 18 stdout)
- **Reviewer(s)**: dyn-state-branching-output.txt
- **Severity**: nit
- **Concern**: Scout notes deliberate deltas: Step 18 drops `--print-stdout`; classify skips key load on empty `ship-pr-state.sh` and uses session fallback—appear deliberate and tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)

### OOS_11: [OUT_OF_SCOPE] case22-classify-empty-state exercises classify guard (no defect)
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: nit
- **Concern**: `case22-classify-empty-state` correctly exercises classify guard for key-empty present file and session fallback; case name slightly misleading (file exists but key-empty).
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision in source)
