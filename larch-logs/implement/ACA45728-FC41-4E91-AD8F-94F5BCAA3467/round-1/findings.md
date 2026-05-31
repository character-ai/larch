Normalizing the supplied reviewer findings into a merged structured list (read-only; no file or repo changes).
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

### FINDING_4: Duplicated STDERR_TAIL_PATH / CODER_LOG_FILE stem selection
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Stem-resolution logic for `STDERR_TAIL_PATH` and `CODER_LOG_FILE` is duplicated between `scripts/ship-pr.sh` and `skills/review-and-fix/scripts/review-implement-step5-loop.sh`. Future KV or ordering changes can desync ship-pr and Step 5 surfacing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract one shared stem-resolution helper used by both.

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

### FINDING_12: Plan-review collector stderr bypasses tail redaction pipeline
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Collector stderr is teed raw to FD 2/4 without the failed-agent tail redaction pipeline. On collect failure after a panel reviewer prints tokens or tmpdir paths to stderr, chat and `plan-review-collector.stderr` may receive unredacted content while implement lanes use lib-redacted tails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Route collector stderr through render_failed_agent_stderr_tail / §3.8-style emission on failure, or document this as an intentionally unredacted design diagnostic channel.

### FINDING_13: `run_codex` tail write lacks cursor-style absent-file guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `run_codex` unconditionally calls `write_failed_agent_stderr_tail` without checking for an existing `${run_dir}/codex.log.stderr-tail`. If `run-external-agent` already wrote a tail, a weak overwrite from the wrapper log is possible (low risk with current `--stderr-sink`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror run_cursor: only write_failed_agent_stderr_tail when ${run_dir}/codex.log.stderr-tail is absent.

### FINDING_14: `test-lint-fix-loop.sh` case 10 omits cursor fallback write path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Harness case 10 does not exercise the cursor fallback `write_failed_agent_stderr_tail` when `.stderr-tail` is absent. A regression could leave Step 5 / ship-pr without a stem despite cursor failure when only `.diag` stderr exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub failure with .diag stderr only; assert write_failed_agent_stderr_tail fallback creates cursor.log.stderr-tail.

### FINDING_15: Implementer agent-failure tests omit redaction bound assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Agent-failure harness cases do not assert line/byte caps or redaction bounds required by plan wording. Unbounded or unredacted tail content could regress in launcher write paths while probe greps still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port line/byte-cap assertions from test-lib-failed-agent-stderr-tail.sh or document lib-only coverage in harness contract.
  - From cursor-specialist-plan-fidelity-output.txt: Add line/byte bound assertions or document reliance on test-lib-failed-agent-stderr-tail in the case header.

### FINDING_16: Lint-fix-loop harness fixture copy list can drift from sources
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The growing list of files copied into lint-fix-loop harness fixtures can drift from `lint-fix-loop.sh` sources. A new sourced file without a harness copy can yield false-green offline tests or false-red CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document sync requirement in test-lint-fix-loop.md or add pre-case check that all sourced files are copied.

### FINDING_17: Cleanup `find-failure-skips-deletion` covers cache pass only
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: important
- **Concern**: The new `find-failure-skips-deletion` case in `skills/cleanup/scripts/test-cleanup.sh` exercises only the cache pass. `/tmp` pattern directories use the same nested `should_remove_by_age` scan before `rm -rf`. A regression breaking the fail-safe only on the tmp branch would not be caught despite docs claiming the fail-safe applies on both passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cleanup-retention-output.txt: Add a mirror case under `LARCH_TEST_TMP_ROOT` with a stale `claude-implement-*` directory, `PATH_PREFIX` pointing at the `write_stub_find_failure` stub, and assert `TMP_REMOVED=0`, the directory still exists, and stderr contains `failed to scan session activity`.

### OOS_1: [OUT_OF_SCOPE] Branch mixes #3227 stderr-tail with #3229 cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-contracts-output.txt, dyn-stderr-tails-output.txt
- **Severity**: latent
- **Concern**: The branch bundles unrelated #3229 cleanup retention work, run-log churn, and broad doc/skill changes alongside #3227 stderr-tail behavior. Isolated review or revert of stderr-tail-only work is harder; plan-to-diff tracing shows substantial unrelated churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split PRs or single feature commit series per issue.
  - From cursor-specialist-plan-fidelity-output.txt: Split or label commits so #3227 PR scope matches the implementation plan surface.
  - From dyn-bash-contracts-output.txt: Commits `2f375cd1e` / `475777f42` carry cleanup (#3229) and run-log churn unrelated to #3227 stderr-tail behavior; the bash-contract review above targets the stderr-tail producer/consumer edits in `3de7ceaaf` and follow-up `f3b107fa6`.
  - From dyn-stderr-tails-output.txt: The branch bundles unrelated #3229 cleanup retention work (`skills/cleanup/scripts/cleanup.sh`, docs, tests). It does not affect stderr-tail integration but widens review surface beyond #3227.

### OOS_2: [OUT_OF_SCOPE] Cursor auth preflight tail gap noted as follow-up only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Cursor auth preflight does not write stderr-tail; only the model-args path does. Preflight failures may have `SIDECAR_LOG` but no `${TRANSCRIPT}.stderr-tail` for step2 emit. Marked out of scope for the #3227 plan as a follow-up if desired (same behavioral gap as in-scope FINDING_1, framed as plan boundary).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: follow-up write_failed_agent_stderr_tail on preflight branch if desired

### OOS_3: [OUT_OF_SCOPE] `_collect_rc` dead state (plan-review collector)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-contracts-output.txt
- **Severity**: latent
- **Concern**: `_collect_rc` in `plan-review-loop.sh` is assigned but never read after the tee/`set -e` fix. Not a surfacing regression by itself; dead state may confuse future readers expecting collector-rc-driven branching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove variable or branch on it if future logic needs explicit collect failure handling.
  - From cursor-specialist-plan-fidelity-output.txt: Use _collect_rc in downstream failure handling or drop the variable with a comment that only the assignment prevents set -e abort.
  - From dyn-bash-contracts-output.txt: `_collect_rc` is assigned but never read; collector failure handling appears unchanged aside from not aborting the assignment under `set -e`. The new harness case still validates the tee path; this is dead state, not a surfacing regression by itself.

### OOS_4: [OUT_OF_SCOPE] Double `write_failed_agent_stderr_tail` on Codex path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-stderr-tails-output.txt
- **Severity**: nit
- **Concern**: `run_codex` / launcher may double-write `${run_dir}/codex.log.stderr-tail` via `run-external-agent` `--stderr-sink` and an explicit `write_failed_agent_stderr_tail`. Redundant work on the same source; low clobber risk with current wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional: skip launcher write when run-external-agent already produced tail.
  - From dyn-stderr-tails-output.txt: `run_codex` may double-write `${run_dir}/codex.log.stderr-tail` (via `run-external-agent.sh` with `--stderr-sink` and the explicit `write_failed_agent_stderr_tail`); redundant but same source, not a clobber risk like `cursor.wrapper.log`.

### OOS_5: [OUT_OF_SCOPE] Step 5 harness gap as accepted plan coverage deferral
- **Reviewer(s)**: dyn-stderr-tails-output.txt
- **Severity**: latent
- **Concern**: Plan acceptance called for Step 5 harness coverage of parse-before-`rm` and terminal-arm surfacing; the branch updates `review-implement-step5-loop.sh` but adds no dedicated offline test (plan allowed documenting the gap). Framed as coverage gap, not a proven runtime wiring bug in the diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Cleanup depth-bound tradeoff (pre-existing, documented)
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: latent
- **Concern**: Activity deeper than five levels does not protect a session directory from deletion. Documented in docs and `SECURITY.md` as intentional conservative disk reclamation, not a branch regression.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] Asymmetric `/tmp` vs cache enumeration (pre-existing)
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: latent
- **Concern**: Cache pass lists all non-symlink top-level entries; `/tmp` pass only considers entries with `-mtime +N`. A `/tmp` directory with fresh top-level mtime but stale contents may never enter removal evaluation, unlike cache shape with the same interior staleness.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] Top-level cache non-directories never removed (pre-existing)
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: nit
- **Concern**: `should_remove_by_age` returns immediately for non-directories; loose files under `larch/sessions/` are never removed. Docs describe directory-oriented removal; not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Cleanup branch delta is mostly test/doc alignment
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: nit
- **Concern**: `cleanup.sh` logic is largely unchanged aside from comments; branch fixes prior doc drift and improves `write_stub_find_failure` (fail only on `-maxdepth 5`). Informational scope note for reviewers tracing #3229 vs runtime behavior.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] Recovery waterfall leaves launcher stdout temp files
- **Reviewer(s)**: dyn-shippr-waterfall-output.txt
- **Severity**: nit
- **Concern**: `run_recovery_waterfall` may leave up to three `recovery-*-launcher-$$.out` files per invocation under `$IMPLEMENT_TMPDIR` without explicit cleanup. Low impact given tmpdir lifecycle.
- **Suggested revisions (informational for voters; coder decides)**:
