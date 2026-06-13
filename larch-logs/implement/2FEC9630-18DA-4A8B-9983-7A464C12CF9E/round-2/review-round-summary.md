# Review Round 2

- Mode: `diff`
- 10 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Makefile `test-auto-fix-plan-commands` still runs deleted shell harness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt, dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: `make test-auto-fix-plan-commands` still invokes `skills/design/scripts/test-auto-fix-plan-commands.sh`, whose `SUBJECT` targets deleted `auto-fix-plan-commands.sh`. The target fails at `bash -n` or before exercising the Python implementation, breaking CI/shard 19 and `scripts/relevant-checks.sh` despite existing pytest coverage for auto-fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Retarget to `pytest -q python/test_plan_quality.py -k auto_fix`
  - From cursor-specialist-edge-cases-output.txt: Retarget Makefile to `pytest -k auto_fix`; update or remove `test-auto-fix-plan-commands.sh` to invoke `python/cli.py plan auto-fix-commands`
  - From cursor-specialist-testing-output.txt: Retarget Makefile to `pytest -k auto_fix` and update or remove the shell harness `SUBJECT`
  - From codex-generic-output.txt: Retarget this Makefile target to `pytest -q python/test_plan_quality.py -k auto_fix`, or update the harness to invoke `python/cli.py plan auto-fix-commands`.
  - From dyn-design-callsite-cutover-output.txt: Retarget the Makefile target to pytest (for example `-k auto_fix`) and either delete or rewrite `test-auto-fix-plan-commands.sh` to stub `python/cli.py plan auto-fix-commands`, matching `test-design-postplan-emit.sh`.


### FINDING_10: `auto-fix-commands` skips `validate_design_tmpdir` allowlist
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `auto-fix-commands` skips `validate_design_tmpdir` allowlist. Same allowlist bypass for `plan-autofix/` and vendor dispatch artifacts under attacker-chosen tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Call `validate_design_tmpdir` at auto-fix entry


### FINDING_11: `plan validate` copies logs without `validate_design_tmpdir` check
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `plan validate` copies logs to `--design-tmpdir` without allowlist check. Writing `validate-plan-commands.log` outside session/tmp allowlist when `DESIGN_TMPDIR` is attacker-controlled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Validate design tmpdir before log copy; keep stable-temp fallback when absent/invalid


### FINDING_12: Revision waterfall pytest coverage far below retired harness parity
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Revision waterfall pytest coverage is far below plan/harness parity. No automated tests for apply-failure restore, emit-plan gate restore, file-replacement fallback, patch apply restore, tier order, heading guard, and related paths. Regressions may ship undetected after shell harness deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port critical revise-waterfall harness scenarios into pytest with fake launchers
  - From cursor-specialist-testing-output.txt: Port high-signal cases from `scripts/test-revise-plan-with-waterfall.sh` using `LARCH_TEST_LAUNCH` seams


### FINDING_15: `validate-plan-commands` fixture suite not ported to pytest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `validate-plan-commands` fixture suite not ported to pytest. Tier 3 dry-run composed skip and other validator edge cases have no automated coverage after shell harness deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Parametrize pytest against validate-plan-commands fixtures or recreate runtime equivalents


### FINDING_2: `test-design-publish.sh` fake `cli.py` lacks `plan validate` handler
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The publish harness fake `python/cli.py` has no `plan validate` handler while `design-publish.sh` calls it. Non-skip publish cases exit 2 with plan validator failed before publish (validator defect tests expect exit 4 but get exit 2 from unexpected CLI args).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add plan validate stub like `test-design-postplan-emit.sh`
  - From cursor-specialist-testing-output.txt: Add plan validate stub matching `test-design-postplan-emit.sh` pattern


### FINDING_21: `plan validate` repo-root resolution unsafe for session tmpdir plans
- **Reviewer(s)**: codex-generic-output.txt, dyn-plan-cli-contracts-output.txt, dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: `plan validate` resolves `--repo-root` via `_repo_root_from(plan.parent)` when callers omit it, then falls back to caller `cwd`. Production callers (`design-postplan-emit.sh`, `design-publish.sh`, `design-driver.sh`) pass plans under `$DESIGN_TMPDIR`, usually outside any git worktree, so `git -C "$DESIGN_TMPDIR"` fails and validation falls back to `Path.cwd()`. The retired `validate-plan.sh` anchored on plugin checkout (`git -C "$SCRIPT_DIR/../../.." rev-parse`). If orchestrator cwd is not the intended consumer repo (background helper, wrong working directory, non-repo cwd), script paths resolve against the wrong tree: false `missing-script` / `unknown-flag` defects, Tier 3 dry-run silently skipped, and Gate B / Step 5c may block or override on bad evidence. `design-driver.sh` computes `REPO_ROOT` but does not forward it into `VALIDATE_PLAN_COMMANDS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Pass `--repo-root "$PLUGIN_ROOT"` from all design validation call sites, or make the CLI default resolve from the plugin root like the retired shell wrapper did.
  - From dyn-plan-cli-contracts-output.txt: Have every shell caller pass an explicit `--repo-root` (for example `$(git -C "$PLUGIN_ROOT" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$PWD")`), or teach `validate_plan_main` to prefer the same plugin-checkout discovery order as `validate-plan.sh` before using cwd.
  - From dyn-design-callsite-cutover-output.txt: Thread an explicit `--repo-root` at every production call site (for example `$(cd "$SCRIPT_DIR/../../.." && pwd -P)` in postplan/publish, and the existing `REPO_ROOT` in `design-driver.sh`), and make `validate_plan_main` fall back to plugin-relative resolution when `--repo-root` is omitted.
  - From dyn-design-callsite-cutover-output.txt: Extend the `VALIDATE_PLAN_COMMANDS` branch to pass `--repo-root "$REPO_ROOT"` (and keep exporting `DESIGN_TMPDIR`) before forwarding `"$@"`.
  - From dyn-design-callsite-cutover-output.txt: Change the default to plugin-relative discovery (for example `_repo_root_from(Path(__file__).resolve().parent.parent)` or equivalent), matching `revise_plan_with_waterfall_main`, and keep `--repo-root` as an override.


### FINDING_22: `test-run-step1-plan-log.sh` still sets `RUN_STEP1_COMPOSE_SH` instead of `RUN_STEP1_COMPOSE_CMD`
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Survivor harness still sets `RUN_STEP1_COMPOSE_SH`, but `scripts/run-step1-plan-log.sh` now only reads `RUN_STEP1_COMPOSE_CMD`. Spy composer is ignored, argv capture file is never written, and `make test-run-step1-plan-log` fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Update all remaining `RUN_STEP1_COMPOSE_SH` uses in this harness to `RUN_STEP1_COMPOSE_CMD`, with the full command override expected by the new script.


### FINDING_3: Stale references to retired plan-quality docs in `skills/design/SKILL.md`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` still advertises deleted sibling docs (`validate-plan-commands.md`, `validate-plan.md`, `auto-fix-plan-commands.md`, `invoke-plan-validator.md`, `check-plan-size.md`, `lint-retired-scripts`). A `/design` agent following those pointers hits missing files; operator doc drift fails acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Repoint to `python/plan_quality.py` and surviving contract docs
  - From codex-generic-output.txt: Restore and update any contract doc that remains authoritative, or remove these sibling pointers and point to `python/plan_quality.py`, `python/cli.py plan ...`, and surviving docs only.


### FINDING_9: `revise-waterfall` skips `validate_design_tmpdir` allowlist
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `revise-waterfall` skips `validate_design_tmpdir` allowlist. Direct CLI call with arbitrary writable directory can create plan-review artifacts outside larch session roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Call `validate_design_tmpdir` at revise-waterfall entry before mkdir/write


