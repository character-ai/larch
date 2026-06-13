# Review Round 1

- Mode: `diff`
- 21 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Drift baseline filename mismatch breaks postplan interoperability
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: Python `plan check-size` reads/writes `$DESIGN_TMPDIR/.larch-drift-baseline.env` and `.larch-drift-baseline.unreadable`, while surviving bash (`lib-drift-baseline.sh`, `design-postplan-emit.sh`) uses `drift-baseline.env` and `.drift-baseline-unreadable`. After Step 2b postplan seeds a baseline, Python check-size will not see it, may re-seed from the current plan, and drift advisories can silently miss real growth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use drift-baseline.env and .drift-baseline-unreadable with the same write-once and unreadable-marker semantics as lib-drift-baseline.sh.
  - From dyn-plan-cli-contracts-output.txt: Use the same filenames as `lib-drift-baseline.sh` (`drift-baseline.env`, `.drift-baseline-unreadable`), implement write-once seeding, and add an integration test that postplan snapshot + later `plan check-size` share one baseline file.


### FINDING_10: Auto-fix prompt embeds raw validator log without secret redaction
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Python auto-fix writes the validator log verbatim into `prompt.md` sent to Codex/Cursor. Untrusted validator output may contain secrets or instruction-like text; a dry-run can print sensitive content into `validate-plan-commands.log` and auto-fix forwards it unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Pipe log through python/cli.py redact secrets with bash-equivalent fallback before writing prompt.md.
  - From codex-specialist-edge-cases-output.txt: Redact with python/cli.py redact secrets, withhold raw text on failure, and wrap as untrusted data.


### FINDING_11: revise-waterfall composes external prompts without untrusted file-block escaping
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `revise-waterfall` embeds plan, accepted findings, and feature text via raw `read_text` instead of the untrusted file-block helper used by `revise-plan-with-waterfall.sh`. Untrusted content can inject delimiter-looking lines or instructions into external reviewer prompts during Step 3 plan revision.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use python/cli.py untrusted file-block for plan findings and feature blocks matching revise-plan-with-waterfall.sh.
  - From codex-specialist-edge-cases-output.txt: Use the existing untrusted file-block helper or equivalent escaped wrapper with the old trust-boundary wording.


### FINDING_12: Parser golden TSV fixtures are not parametrized in pytest
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: Eleven to thirteen `fixtures/parse-plan-commands` golden plan/TSV pairs exist but pytest only has hand-written spot checks. Parser regressions against byte-exact TSV contracts (including heredoc line numbers, `parse_note` placement, duplicate `updated_flag` rows) will not be caught before `/design` validation false-passes or false-fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add parametrized golden TSV tests for every fixtures/parse-plan-commands pair before deleting shell coverage.
  - From cursor-specialist-testing-output.txt: Parametrize all fixture plan/TSV pairs and assert exact render_plan_command_tsv output.
  - From codex-specialist-testing-output.txt: Parametrize every parser fixture and fix parser output until exact TSV parity is restored
  - From dyn-plan-cli-contracts-output.txt: Parametrize `python/test_plan_quality.py` over the ported fixtures (exact TSV bytes) before deleting the shell harness/fixtures, per the plan acceptance criteria.


### FINDING_13: Auto-fix pytest coverage only exercises unavailable-vendor paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Bash harness scenarios for dispatch alternation, tmpdir/repo guards, and revalidation were not ported. CI can be green while production auto-fix is non-functional and unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port dispatch alternation tmpdir/repo guard and revalidation tests from test-auto-fix-plan-commands.sh using LARCH_AUTOFIX_DISPATCH_SH stubs.


### FINDING_14: Broad plan-quality pytest gaps leave retired harness scenarios unported
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required pytest coverage blocks are mostly missing (Tier 3, no-`DESIGN_TMPDIR` log path, plan-size drift, auto-fix Gate B, revise restore paths). Retired shell harnesses (~3000 lines) are no longer invoked by `make lint`; many edge cases from the implementation plan have zero automated coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port harness scenarios listed in the plan into test_plan_quality.py before deleting shell tests.


### FINDING_15: Step 3 loop harness never tests the default Python revise-waterfall path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-review-design-step3-loop.sh` cases all set `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`. A broken default `python/cli.py plan revise-waterfall` invocation would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a case with override unset and spy on plan revise-waterfall argv/stdout contract.


### FINDING_16: Postplan emit harness still stubs retired shell validators
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-design-postplan-emit.sh` stubs `invoke-plan-validator.sh` / `check-plan-size.sh` while production calls `python/cli.py plan validate` and `plan check-size`. Harness assertions target shell stubs; behavior is non-deterministic relative to real CLI forwarding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update fake cli.py to stub plan validate and plan check-size and align CALL_LOG/KV assertions.


### FINDING_18: check-size does not catch unreadable drift baseline read errors
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Python `plan check-size` reads the drift baseline without catching `OSError`. An unreadable baseline can crash the command before warning and drift KVs are emitted, breaking fail-closed recovery semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Catch baseline read errors and route through recovery or unreadable-marker handling with tests


### FINDING_19: plan check-size skips larch_design_tmpdir_validate allowlist checks
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: Python only checks `design_tmpdir.is_dir()` and accepts any directory path. The bash contract rejects paths outside the cache/tmp allowlist with rc **3** and no `PLAN_SIZE_STATUS`; Python diverges on symlink/CR-LF and allowlist semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: Port the allowlist / symlink / CR-LF checks from `scripts/lib-design-tmpdir.sh` (or call a small shared Python helper) before plan IO, preserving rc **3** vs rc **2** semantics.


### FINDING_2: plan auto-fix-commands never launches production Codex/Cursor vendors
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: When `LARCH_AUTOFIX_DISPATCH_SH` is unset, Python auto-fix sets `dispatch_rc=1` instead of invoking real vendor launchers even with `--codex-present true` / `--cursor-present true`. Every attempt is treated as dispatch failure and returns `AUTOFIX_STATUS=exhausted`, so `/design` validator auto-fix via `design-step-validator-autofix.sh` never repairs plans in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Port the old Codex and Cursor dispatch paths into auto_fix_plan_commands_main with the same timeout, workspace, prompt, timing, and sidecar handling.
  - From cursor-specialist-edge-cases-output.txt: Port live dispatch_vendor_fix from auto-fix-plan-commands.sh into auto_fix_plan_commands_main; keep LARCH_AUTOFIX_DISPATCH_SH as test-only override.
  - From codex-specialist-edge-cases-output.txt: Port the real Codex and Cursor launcher branches and keep the dispatch override only as a test seam.
  - From codex-specialist-testing-output.txt: Port old per-vendor dispatch or call existing launcher surfaces and add a no-override integration test
  - From dyn-design-callsite-cutover-output.txt: Port the bash `dispatch_vendor_fix` paths (Codex exec + Cursor external agent, timing/token sidecars) into `auto_fix_plan_commands_main`, keeping `LARCH_AUTOFIX_DISPATCH_SH` only as a test override.


### FINDING_20: Drift baseline write failures abort instead of emitting WARN and continuing
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: Bash `larch_drift_baseline_write_once` emits `WARN=check-plan-size: could not write drift baseline; proceeding without drift trigger` and continues with rc **0**. Python `_atomic_write` raises and aborts the command on baseline write failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: Catch baseline write failures, emit the same `WARN` KV, leave `trusted=false` / `DRIFT_TRIGGER_FIRED=false`, and return rc **0** with the rest of the size KVs.


### FINDING_21: VALIDATE_LOG_FILE without DESIGN_TMPDIR lacks pytest coverage
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: `plan validate` with `VALIDATE_LOG_FILE` set but no `--design-tmpdir`/env uses `tempfile.mkstemp`; only the design-tmpdir log path is tested. Postplan/publish callers depend on a stable, post-exit readable log when tmpdir is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: Add a test that runs `plan validate` with no `--design-tmpdir` / env, asserts `VALIDATE_LOG_FILE` is readable after exit, and that the path is not removed by command teardown.


### FINDING_22: design-driver.sh validate branch omits DESIGN_TMPDIR handoff
- **Reviewer(s)**: dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: `VALIDATE_PLAN_COMMANDS` calls `plan validate "$@"` without exporting `DESIGN_TMPDIR` or passing `--design-tmpdir "$DESIGN_TMPDIR"`. Evidence lands in a temp log instead of `$DESIGN_TMPDIR/validate-plan-commands.log`, breaking the auto-fix evidence chain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-callsite-cutover-output.txt: Before the validate branch, `export DESIGN_TMPDIR` and/or always pass `--design-tmpdir "$DESIGN_TMPDIR"` plus `--plan-file` in the driver dispatch.


### FINDING_23: design-step-validator-autofix resolves repo root via PWD instead of git toplevel
- **Reviewer(s)**: dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: Auto-fix passes `--repo-root "$PWD"` while the retired bash helper resolves repo root via `git rev-parse` with `PLUGIN_ROOT` fallback. If the design wrapper cwd is not the consumer repo root, Tier 2 script-path validation during revalidation can target the wrong tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-callsite-cutover-output.txt: Resolve repo root the same way as the bash helper (git toplevel, else `CLAUDE_PLUGIN_ROOT`) and pass that to `plan auto-fix-commands`.


### FINDING_4: Heredoc parser TSV line-number contract diverges from retired awk behavior
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Python parser assigns `source_line` using physical line numbers after heredoc bodies, while the retired awk parser used compressed post-heredoc line numbering. Golden TSV output for commands following heredocs changes, breaking byte-compatible validation evidence unless the contract and all fixtures are intentionally updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Preserve the awk line-number quirk or intentionally update the contract and all golden fixtures.
  - From codex-specialist-edge-cases-output.txt: Match the retired compressed line-number mapping or update all dependent fixtures and consumers.


### FINDING_5: Absorbed shell surfaces still ship without migration manifest entries
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retired validators, parser, plan-size, auto-fix, optional-trailer, and composer shell scripts remain in the tree and are absent from `python/migrated-scripts.tsv`. Dual bash/Python implementations can ship to consumers, and `lint-retired-scripts` cannot enforce retirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Delete absorbed files after parity and append every retired path to python/migrated-scripts.tsv with the tracking issue id.
  - From codex-specialist-testing-output.txt: Delete absorbed files after parity, append them to migrated-scripts.tsv, and complete stale-reference cleanup


### FINDING_6: Makefile survivor integration targets no longer exercise shell harnesses
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: Targets such as `test-design-postplan-emit`, `test-design-publish`, and `test-design-driver` now run thin pytest subsets instead of the documented bash harnesses. CI can pass while broken shell wiring (`VALIDATE_LOG_FILE` parsing, quiet capture, `PLUGIN_ROOT` bootstrap, merged postplan rc branches, publish exit semantics) goes undetected. Multiple targets also collapse onto overlapping `validate_plan` / `optional_trailer` / `compose_plan_goals_test` selectors, giving false confidence across distinct workflows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Restore the survivor shell harness targets and keep pytest selections for absorbed pure Python surfaces.
  - From cursor-specialist-testing-output.txt: Restore bash harness execution for those targets and update stubs to intercept python/cli.py plan verbs per the plan.
  - From cursor-specialist-testing-output.txt: Split coverage: distinct pytest modules per target or reinstate per-harness bash runs with non-overlapping assertions.
  - From codex-specialist-testing-output.txt: Restore and update survivor shell harness targets or add subprocess tests that execute the actual shell scripts
  - From dyn-design-callsite-cutover-output.txt: Either restore shell harness execution in Makefile targets (with Python CLI stubs in the fake dispatcher) or add pytest integration tests that invoke the real shell drivers with stubbed `python/cli.py plan` verbs.


### FINDING_7: test-gate-b-dedup-plan no longer runs the Bash Gate B harness
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The Makefile target no longer invokes `skills/design/scripts/test-gate-b-dedup-plan.sh`. Modified shell orchestration in `gate-b-dedup-plan.sh` can break while optional-trailer unit tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Point test-gate-b-dedup-plan back to the shell harness and keep optional-trailer pytest under helper coverage.


### FINDING_8: test-run-step1-plan-log no longer runs the Step 1 shell launcher harness
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The Makefile target no longer runs `scripts/test-run-step1-plan-log.sh`. Plugin-root resolution, run-id resolution, atomic output moves, run-log writes, and override behavior can break while `compose_plan_goals_test` passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Restore scripts/test-run-step1-plan-log.sh for this target and keep composer unit tests under test-compose-plan-goals-test.


### FINDING_9: Python auto-fix drops tmpdir/repo mutation guards and ignores trailer snapshot failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: The Python auto-fix port omits tmpdir manifest backup/restore, repo dirty-tree snapshot/delta checks, and post-dispatch symlink guards present in bash auto-fix. `gate-b-dedup-plan.sh --snapshot-trailers` is invoked with `check=False`, so snapshot failures are ignored before vendor edits. A vendor can mutate non-target `DESIGN_TMPDIR` files or the consumer git worktree and still reach revalidation if plan validation passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port tmpdir_guard_* git_status_snapshot check_repo_dirty_delta and post-dispatch symlink checks from auto-fix-plan-commands.sh; restore and fail closed before accepting ok.
  - From codex-specialist-edge-cases-output.txt: Restore before/after repo snapshots, tmpdir manifests, restore logic, and guard failure statuses.
  - From codex-specialist-testing-output.txt: Port tmpdir manifest backup/restore and git-status delta checks with mutation tests
  - From dyn-design-callsite-cutover-output.txt: Port `tmpdir_guard_*`, `git_status_snapshot`, `check_repo_dirty_delta`, and trailer-snapshot failure handling from `skills/design/scripts/auto-fix-plan-commands.sh` (lines 460-534), and fail closed on nonzero gate-b snapshot rc.


