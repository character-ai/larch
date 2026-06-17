# Review Round 3

- Mode: `diff`
- 11 accepted, 9 rejected (4 neutral)

## Accepted Findings

### FINDING_1: Agentic `local-unfixable` mapping loses stable reason token and operator context
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: After agentic delegate emits `STATUS=local-unfixable`, `_agentic_fix_result` / `monitor()` surfaces `NEEDS_USER_INPUT` with job-name detail only (e.g. `gitleaks`) instead of a stable `local-unfixable` reason token. `ship.py` cannot normalize `needs_user_reason` to `local-unfixable`. Operator bail after `FIX_ATTEMPTED=true` may show only job names without a redacted FAIL excerpt or threaded exhaustion detail comparable to cycle-cap exhaustion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Thread failure log through agentic KV or EXHAUSTED_DETAIL_FILE and map like cycle-cap exhaustion
  - From codex-generic-output.txt: Return `FixResult(status="local-unfixable", unfixable=(...))`, or prefix the detail as `local-unfixable: gitleaks` before it reaches `monitor()`.


### FINDING_11: CI agentic fix forbidden-path guards omit protected repo files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `coder_delta_guards` in `python/ci_agentic_fix.py` cover only `.gitmodules` and submodule paths, not other protected surfaces (e.g. `.claude-plugin/plugin.json`). Write-capable Opus CI fixers could modify and push protected files if edits appear in `delta_paths`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reuse Step 2 protected-path checks in coder_delta_guards or stage_and_push preflight


### FINDING_12: Lint-fix forbidden-path guards omit protected repo files
- **Reviewer(s)**: dyn-lint-claude-output.txt
- **Severity**: important
- **Concern**: `run_lint_fix` builds `forbidden` from `.gitmodules` and submodule paths only. The write-capable `launch-claude-lint-fix` path bypasses PreToolUse hooks; a successful Opus edit to `plugin.json` or other hook-protected paths can flow through post-dispatch guards, land in `delta_paths`, and be auto-committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-lint-claude-output.txt: Extend the lint-fix forbidden-path set to include `config.PLUGIN_JSON_PATH` (and any other hook-protected paths you want parity with), mirror the Step 2 protected-path policy in `_post_dispatch_forbidden_revert` and committed-path checks, and add a regression test that a Claude lint-fix touch of `plugin.json` is reverted and fails closed.


### FINDING_15: `SKILL.md` still routes `ci-fix-exhausted` through autonomous CI-fix
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Main `/implement` routing prose at `skills/implement/SKILL.md:744` still lists `ci-fix-exhausted` in the autonomous main-agent CI-fix sub-procedure, contradicting the Step 12d operator-bail contract and risking orchestrator execution of the retired path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Remove `ci-fix-exhausted` from that autonomous list and route it directly to Step 12d after escalation recording.


### FINDING_2: `test_ci_monitor.py` skipped integration tests lack agentic replacement coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-ci-delegate-output.txt
- **Severity**: important
- **Concern**: Sixteen `evaluate_failure` / `monitor()` CI-fix integration tests are skipped for the agentic delegate with no parity replacement. Regressions in `_agentic_fix_result` KV mapping, `ci_fix_rebase_pending` early-branch isolation, `rebase-required` → `goto_rebase`, `FIX_ATTEMPTED` promotion, delegate `cwd`/`--repo-root` threading, and single-delegate invocation can ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add stubbed-delegate tests per plan matrix; remove or replace skipped tests
  - From cursor-specialist-testing-output.txt: Add plan-specified agentic-delegate tests; remove skips only after parity.
  - From dyn-ci-delegate-output.txt: Unskip or re-home the high-value cases (pending push-only path does not re-enter agentic, `rebase-required` → `goto_rebase`, `FIX_ATTEMPTED` promotion, missing `cwd`/`implement_tmpdir` fail-closed) against `_agentic_fix_result` / `evaluate_failure` stubs.


### FINDING_20: Explicit conflict loop uses wrong failure-class parser vs `run_waterfall`
- **Reviewer(s)**: dyn-conflict-loop-output.txt
- **Severity**: important
- **Concern**: The explicit conflict tier loop classifies launcher failures with `agents.effective_failure_class(attempt)`, but stock `run_waterfall` uses `agents.parse_launcher_failure_class(attempt.failure_log)` when `failure_log` is set. When the capture file exists but omits `LAUNCHER_FAILURE_CLASS=` (timeout/kill, truncated stdout), `parse_launcher_failure_class` defaults to `health` and continues to Codex/Cursor, while `effective_failure_class` falls back to `other` and triggers first-tier short-circuit after Claude only. Production-path divergence from the prior waterfall contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-conflict-loop-output.txt: Mirror `run_waterfall` exactly: `failure_class = agents.parse_launcher_failure_class(attempt.failure_log) if attempt.failure_log is not None else agents.effective_failure_class(attempt)` before the `index == 0` short-circuit check, and add a `test_rebase.py` case matching `test_waterfall_continues_when_log_missing_failure_class_kv` in `python/test_agents.py`.


### FINDING_21: Conflict marker detection ignores separator and diff3 markers
- **Reviewer(s)**: dyn-conflict-loop-output.txt
- **Severity**: important
- **Concern**: `_path_has_conflict_markers` only matches `<<<<<<<` and `>>>>>>>` at line start, ignoring `=======` and diff3 `|||||||`. A fixer can strip outer markers, leave separators, pass staging guards, and reach `git rebase --continue` with corrupted conflict content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-conflict-loop-output.txt: Treat all standard Git conflict marker lines as unresolved (`<<<<<<<`, `=======`, `>>>>>>>`, `|||||||`), e.g. extend `_CONFLICT_MARKER_RE` to cover them, and add tests for partial-marker files that must not be staged.


### FINDING_23: Missing `launch_claude_lint_fix` and write-capable `launch_claude_ci` argv tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-lint-claude-output.txt
- **Severity**: important
- **Concern**: `python/test_agents.py` has no `launch-claude-lint-fix` argv-contract tests and `launch_claude_ci` tests omit opus default and write-capable argv (`-p`, `Edit`/`Write`). Lint-fix could route through wrong launcher/model; CI would not catch argv or permission regressions. Docs claim harness coverage that is not wired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add plan-required launch_claude_lint_fix and write-capable launch_claude_ci tests.
  - From dyn-lint-claude-output.txt: Add `test_launch_claude_lint_fix_*` cases mirroring the CI launcher harness so a regression cannot silently widen tool permissions or move prompts back onto argv.


### FINDING_26: Stall-recovery test and harness gaps for `ci-fix-exhausted` contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-generic-output.txt
- **Severity**: latent
- **Concern**: Python and Bash stall-recovery classifiers/harnesses lack full `ci-fix-exhausted` contract assertions (`RESUME_HINT=none`, `MAX_ATTEMPTS=0`, `FAILURE_CLASS=unrecoverable`). Case 20l in `test-stall-recovery-report-2.sh` still expects precise test evidence under `ci-fix-exhausted` to resume `step8-shippr`, contradicting the shell classifier's unrecoverable-before-test-pattern behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert RESUME_HINT=none and MAX_ATTEMPTS=0 for ci-fix-exhausted.
  - From cursor-specialist-testing-output.txt: Extend case 7l3 and add ci-fix-exhausted|0|none to retry-policy table.
  - From codex-generic-output.txt: Update case 20l to expect `FAILURE_CLASS=unrecoverable` and `RESUME_HINT=none`, or remove the stale “precise evidence outranks” case.


### FINDING_3: Missing rebase explicit-loop health-failure continuation test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: No test asserts that a first-tier Claude health failure in the explicit conflict tier loop continues to Codex/Cursor (two launches). A misclassification that short-circuits on health would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add claude health fail then codex succeed test asserting two launches


### FINDING_9: `stall_recovery.py` classifies `ci-fix-exhausted` after generic test/lint evidence
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: A `ci-fix-exhausted` bail with a detail log containing common CI text (`pytest`, `ruff`, etc.) can match `test-failure` or `lint-failure` before the unrecoverable branch runs, yielding a resume hint instead of `RESUME_HINT=none` and reintroducing auto-resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Check `bail == "ci-fix-exhausted"` before generic test/lint evidence matching.


