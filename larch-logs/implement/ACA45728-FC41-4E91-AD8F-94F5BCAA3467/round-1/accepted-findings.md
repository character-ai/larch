### FINDING_1: Cursor auth preflight omits stderr-tail write
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-contracts-output.txt, dyn-stderr-tails-output.txt
- **Severity**: important
- **Concern**: On Cursor auth preflight failure, diagnostics land in `SIDECAR_LOG` and the launcher exits with `LAUNCHER_EXIT` set, but unlike the model-args early-exit path there is no `write_failed_agent_stderr_tail` to `${TRANSCRIPT_PATH}.stderr-tail`. `run-external-agent` does not run on this path. Step 2 `emit_bailed` surfaces chat tails only via the tail file (`emit_failed_agent_stderr_tail_larch_err`), so operators see a `SIDECAR_LOG=` KV without the fenced stderr tail in chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true before KV emit on preflight failure (mirror model-args branch).
  - From cursor-specialist-correctness-output.txt: Add write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true before preflight exit 0 (same as MODEL_ARGS_RC branch).
  - From cursor-specialist-edge-cases-output.txt: Add write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true before preflight exit 0; extend test-cursor-implementer K3 to assert .stderr-tail
  - From dyn-bash-contracts-output.txt: Add the same `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` immediately before the preflight early `exit 0`, mirroring the model-args branch.
  - From dyn-stderr-tails-output.txt: Mirror the model-args branch: call `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` before the preflight `exit 0`, and extend K3 (or add a sibling case) to assert a non-empty `${TRANSCRIPT}.stderr-tail`.


### FINDING_10: Recovery waterfall `LAUNCHER_EXIT` surfacing without tier-failure gating
- **Reviewer(s)**: dyn-stderr-tails-output.txt, dyn-shippr-waterfall-output.txt
- **Severity**: latent
- **Concern**: Recovery waterfall now parses `LAUNCHER_EXIT` and calls `_surface_ci_stderr_tail` when `launcher_exit -ne 0` or a stderr-tail exists, but tier advancement still keys primarily on shell `tier_rc`. CI launchers often `exit 0` with failure encoded in stdout (`LAUNCHER_EXIT`). The common shape `tier_rc=0` with `launcher_exit≠0` can surface a tail and still run phase verifier work before advancing, diverging from `run_ci_fix_vendor` (rollback and next tier after launcher failure). Operators may see a failed-agent tail followed by unrelated verifier work on a tier that already failed at the agent layer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stderr-tails-output.txt: After surfacing, `continue` to the next tier when `launcher_exit -ne 0` (and optionally when `-s "${output}.stderr-tail"` without a successful launcher contract), before detached-HEAD / verify logic.
  - From dyn-shippr-waterfall-output.txt: After surfacing on `launcher_exit -ne 0` or a non-empty `${output}.stderr-tail` (with `tier_rc=0`), call `recovery_waterfall_paths_delta_revert` and `continue` before detached-head/verify—matching the `tier_rc -ne 0` branch—unless a documented exception requires verify on agent failure.


### FINDING_11: Recovery waterfall stdout capture / surfacing lacks integration harness
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-shippr-waterfall-output.txt
- **Severity**: important
- **Concern**: Recovery waterfall’s per-tier `launcher_stdout` capture, `LAUNCHER_EXIT` parsing, and tri-condition surfacing gate are implemented but not covered by an integration case in `test-ship-pr.sh` as the plan testing strategy describes. Regressions that drop parsing, use the wrong stem, or surface without advancing tiers would not be caught while existing `run_ci_fix_vendor` ordering tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a recovery-waterfall stub case asserting tail emission before recovery_waterfall_paths_delta_revert when only launcher_exit or stderr-tail indicates failure.
  - From dyn-shippr-waterfall-output.txt: Add a `test-ship-pr.sh` case stubbing `launch-cursor-ci.sh` with `exit 0` + `LAUNCHER_EXIT=1`, a pre-seeded `${output}.stderr-tail`, and `run_recovery_waterfall` (or a minimal sourced wrapper), asserting the probe reaches caller stderr and that the waterfall advances to the next tier without invoking the verifier on the failed tier.


### FINDING_14: `test-lint-fix-loop.sh` case 10 omits cursor fallback write path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Harness case 10 does not exercise the cursor fallback `write_failed_agent_stderr_tail` when `.stderr-tail` is absent. A regression could leave Step 5 / ship-pr without a stem despite cursor failure when only `.diag` stderr exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub failure with .diag stderr only; assert write_failed_agent_stderr_tail fallback creates cursor.log.stderr-tail.


### FINDING_17: Cleanup `find-failure-skips-deletion` covers cache pass only
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: important
- **Concern**: The new `find-failure-skips-deletion` case in `skills/cleanup/scripts/test-cleanup.sh` exercises only the cache pass. `/tmp` pattern directories use the same nested `should_remove_by_age` scan before `rm -rf`. A regression breaking the fail-safe only on the tmp branch would not be caught despite docs claiming the fail-safe applies on both passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cleanup-retention-output.txt: Add a mirror case under `LARCH_TEST_TMP_ROOT` with a stale `claude-implement-*` directory, `PATH_PREFIX` pointing at the `write_stub_find_failure` stub, and assert `TMP_REMOVED=0`, the directory still exists, and stderr contains `failed to scan session activity`.


### FINDING_2: `run_cursor` early exits omit stderr-tail stem / KV
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stderr-tails-output.txt
- **Severity**: latent
- **Concern**: `run_cursor` returns early on model-args, auth, or wrap setup failure without setting `_LINT_FIX_STDERR_TAIL_STEM` or emitting `STDERR_TAIL_PATH`. Cursor-only lint-fix failures on those paths yield `main-agent-required` / `dispatch-failed` without a stem for ship-pr, Step 5, or other callers to surface tails to chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Write tail + set stem on early failures from available logs, or document as accepted gap.
  - From cursor-specialist-correctness-output.txt: On early return paths capture stderr to a file set _LINT_FIX_STDERR_TAIL_STEM and/or write_failed_agent_stderr_tail before return 1.
  - From cursor-specialist-edge-cases-output.txt: Add stem capture on early-return paths or document exclusion; add harness case for cursor-only pre-dispatch failure
  - From dyn-stderr-tails-output.txt: On those early failures, append model/auth stderr to a known file under `$run_dir` (e.g. `cursor.wrapper.log` or a dedicated preflight log), call `write_failed_agent_stderr_tail` with stem `$run_dir/cursor.log`, set `_LINT_FIX_STDERR_TAIL_STEM`, and add a `test-lint-fix-loop.sh` case for cursor-only preflight failure.


### FINDING_3: `_surface_ci_stderr_tail` re-source silences later emits
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-contracts-output.txt
- **Severity**: important
- **Concern**: `_surface_ci_stderr_tail` re-sources `lib-failed-agent-stderr-tail.sh` on every call. The library idempotency guard uses `return 0` when `LARCH_FAILED_AGENT_STDERR_TAIL_LOADED` is already set. When invoked from a function, that `return` exits `_surface_ci_stderr_tail` before `emit_failed_agent_stderr_tail_larch_err` runs. The first surfacing call in a `ship-pr.sh` process works; later calls in the same process are silent no-ops. Multi-tier paths (`run_ci_fix_vendor`, `run_recovery_waterfall`) can leave later `${stem}.stderr-tail` files on disk without emitting them to chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Source lib-failed-agent-stderr-tail.sh once at ship-pr top; keep helper as emit-only.
  - From dyn-bash-contracts-output.txt: Source `lib-failed-agent-stderr-tail.sh` once at `ship-pr.sh` startup (with a caller-side `[[ -z "${LARCH_FAILED_AGENT_STDERR_TAIL_LOADED:-}" ]]` guard if needed), and have `_surface_ci_stderr_tail` only call `emit_failed_agent_stderr_tail_larch_err "$stem" || true` without re-sourcing. Alternatively, change the library guard to skip re-definition without `return` when already loaded (e.g. wrap the body in `if [[ -z "${LARCH_FAILED_AGENT_STDERR_TAIL_LOADED:-}" ]]; then …; LARCH_FAILED_AGENT_STDERR_TAIL_LOADED=1; fi`), which matches the plan’s “source once” intent.


### FINDING_5: `_collect_rc` assigned but never read
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: In `skills/design/scripts/plan-review-loop.sh`, `_collect_rc` is written but never consumed. Dead state obscures that only the `||` guard matters for `set -e` on the collector assignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use || true or branch on _collect_rc where collector failure is handled.


### FINDING_6: Step 5 stderr-tail parse/surface contract lacks harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `review-implement-step5-loop.sh` implements parse-before-`rm`, stem stash, and terminal-arm surfacing, but no focused harness asserts that contract. Regressions (parse after `rm`, broken `step5_surface_lint_stderr_tail` guard, empty-stem `set -e` abort) could ship with only ship-pr or lint-fix-loop tests green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add focused harness case or document in harness notes.
  - From cursor-specialist-correctness-output.txt: Add focused test stubbing lint-fix stdout with STDERR_TAIL_PATH= asserting FD-2 fence before final envelope.
  - From cursor-specialist-testing-output.txt: Add parsers cases for new KV lines; sourced test for step5_surface_lint_stderr_tail with seeded .stderr-tail under set -e.
  - From cursor-specialist-edge-cases-output.txt: Add test-review-and-fix.sh case for STDERR_TAIL_PATH stash and caller-scope emit with empty-stem no-op
  - From cursor-specialist-plan-fidelity-output.txt: Extend test-review-and-fix.sh parsers with STDERR_TAIL_PATH + optional step5_surface_lint_stderr_tail emit cases, or document the contract in review-implement-step5-loop.md.


### FINDING_7: Redundant third clause in `run_lint_fix_loop_capture` surfacing gate
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: In `scripts/ship-pr.sh` `run_lint_fix_loop_capture`, the `[[ -z "$lint_status" ]] && [[ "$rc" -ne 0 ]]` branch is redundant with the leading `[[ "$rc" -ne 0 ]]` check, adding noise without new behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove redundant clause or clarify intent.
  - From cursor-specialist-edge-cases-output.txt: Remove redundant clause or define a distinct trigger for rc=0 malformed output


### FINDING_8: CI stderr-tail tests stop at helper unit level
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shippr-waterfall-output.txt
- **Severity**: important
- **Concern**: New or extended `test-ship-pr.sh` coverage exercises `_surface_ci_stderr_tail` (and related helpers) in isolation, not the plan-required fix-loop choke points (`run_ci_fix_vendor`, recovery waterfall) with stubbed failing launchers and `${tier_out}` / `${output}` stems. Wiring regressions (helper present but not called at tier_out, wrong call order relative to rollback) could pass unit tests and still fail in production CI-fix paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add stub failing launch-*-ci.sh through run_ci_fix_vendor asserting tail on caller stderr at tier_out.
  - From cursor-specialist-testing-output.txt: Add stub CI launcher + pre-seeded ${tier_out}.stderr-tail; exercise fix-loop/recovery paths; assert tail on harness stderr when tier_rc=0 and LAUNCHER_EXIT!=0.
  - From cursor-specialist-plan-fidelity-output.txt: Add an integration case through run_ci_fix_vendor / _ci_fix_waterfall with a stub launcher, real ${tier_out}.stderr-tail producer path, and caller stderr assertion at each failure exit including first-fixer-non-health return 1.
  - From dyn-shippr-waterfall-output.txt: Add a `test-ship-pr.sh` case stubbing `launch-cursor-ci.sh` with `exit 0` + `LAUNCHER_EXIT=1`, a pre-seeded `${output}.stderr-tail`, and `run_recovery_waterfall` (or a minimal sourced wrapper), asserting the probe reaches caller stderr and that the waterfall advances to the next tier without invoking the verifier on the failed tier.


### FINDING_9: Step 2 `emit_bailed` stderr-tail surfacing untested end-to-end
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No harness asserts that `emit_bailed` in `step2-implement.sh` surfaces a stderr tail to chat. Removing `emit_failed_agent_stderr_tail_larch_err` from `emit_bailed` would not fail `test-codex-implementer`, `test-cursor-implementer`, or `test-step2-dispatch`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend test-step2-dispatch or implementer harness: stub launcher + .stderr-tail; run step2-implement.sh; grep fenced tail on dispatcher stderr.


