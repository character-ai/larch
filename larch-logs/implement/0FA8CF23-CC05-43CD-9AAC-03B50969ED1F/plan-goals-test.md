## Goal
Implement issue #5286: [IMPLEMENTING] [BUG] checks repair-loop produces no stdout while lint-fix agent runs, appears hung for 10-40 minutes.

## Implementation Plan
## Summary

`checks repair-loop` produces zero stdout for the entire duration of the lint-fix agent run (10–40+ minutes for pyright step3 failures), making it indistinguishable from a hang. The orchestrator observes an empty task-output file for this entire window and has no mechanism to distinguish "working silently" from "truly stuck."

## Original report

The command `python3 python/cli.py checks repair-loop --tmpdir ... --site step3 --checks-log step3-1.redacted.log` was invoked after step3 detected pyright type errors. The task-output file remained empty (1 blank line) for several minutes, which appeared to be a hang. Expected behavior: nearly instant `NEXT_ACTION=main-agent-edit` for pyright errors. After ~40 minutes the command eventually completed with `NEXT_ACTION=continue LOOP_STATUS=ok`, indicating it had successfully dispatched and completed a lint-fix agent run.

## Reproduction scenario

1. Run `/implement` on a plan that produces pyright type errors in new Python test files.
2. Step 3 checks fail with `FAILURE_REASON=checks-failed PHASE=pre-commit`.
3. Manually (or via the orchestrator) invoke `checks repair-loop --site step3 --checks-log <redacted-log>`.
4. Observe: stdout file remains empty for the entire lint-fix agent duration (10–40+ minutes).
5. Eventually the loop completes with either `NEXT_ACTION=continue` or `NEXT_ACTION=main-agent-edit`.

## Expected behavior

The repair-loop should emit at least periodic progress lines (heartbeats, elapsed time, or a "dispatching lint-fix agent" breadcrumb) so the orchestrator and operator can distinguish active work from a true hang. Alternatively, it should return `NEXT_ACTION=main-agent-edit` immediately for pyright-class failures that require main-agent intervention, rather than silently spawning an external lint-fix agent first.

## Observed behavior

- Stdout file stays at 0 bytes (1 blank line) for the full duration of `run_lint_fix` → external agent run.
- No progress indicators, no heartbeats, no intermediate `STATUS=` lines.
- Only when the entire loop finishes does stdout flush: `NEXT_ACTION=continue\nLOOP_STATUS=ok\n`.
- This is visually identical to a stuck/deadlocked process.

## Root cause analysis

`checks_repair_loop_main` (`python/checks.py:1249`) calls `run_check_fix_loop` with `dispatch_first=True` (`checks.py:1302`). Inside `run_check_fix_loop` (`checks.py:2419`), the first action is `fixer(redacted_log_for_dispatch)` which calls `run_lint_fix` (`checks.py:1935`). `run_lint_fix` dispatches an external lint-fix agent (Claude subprocess via `run_parent` worker). This external agent runs synchronously (blocking the repair-loop process) and produces no intermediate output to the repair-loop's stdout. The repair-loop's stdout only flushes when `run_check_fix_loop` returns and `checks_repair_loop_main` prints its final `NEXT_ACTION=` and `LOOP_STATUS=` lines (`checks.py:1311–1312`).

The silence is structural: `run_check_fix_loop` is a blocking call that does not yield or emit progress while the external agent runs.

## Evidence

- Task output file `bdpvhgr6t.output` contained only a blank line for ~40 minutes during the run.
- After completion it contained `NEXT_ACTION=continue\nLOOP_STATUS=ok\n`, confirming the loop succeeded (lint-fix agent fixed the pyright errors, re-check passed).
- `checks_repair_loop_main` at `checks.py:1311` prints `NEXT_ACTION=` only after `run_check_fix_loop` returns — no intermediate flushes.
- `run_check_fix_loop` at `checks.py:2442–2468` calls `fixer()` synchronously; no progress is written to stdout during this call.
- The specific failures were pyright type errors in `python/analyze_issues.py:2246`, `python/test_findings_ledger.py:148,150`, and `python/test_voting.py:209` — all fixable but requiring a lint-fix agent invocation.

## Affected files

- `python/checks.py` — `checks_repair_loop_main` (line 1249), `run_check_fix_loop` (line 2419), `run_lint_fix` (line 1935): the silent dispatch chain with no intermediate output.

## Suggested fix(es)

Two non-exclusive options:

1. **Emit progress heartbeats**: Before calling `fixer()` inside `run_check_fix_loop`, print a line such as `STATUS=dispatching-lint-fix site=<site>` to stdout (then flush). This immediately distinguishes "working" from "stuck" for the orchestrator. Repeat at intervals (e.g., every 60s via a background thread or subprocess) if feasible.

2. **Fast-classify pyright-only failures**: In `run_lint_fix` (or in `checks_repair_loop_main` before calling `run_check_fix_loop`), detect when the checks log contains only pyright type errors (not fixable by automated formatters) and return `FixOutcome(status="main-agent-required")` immediately. The repair-loop would then emit `NEXT_ACTION=main-agent-edit` in seconds rather than dispatching a long-running agent for failures that the main agent must address anyway.

Option 2 also avoids the latency cost of an unnecessary lint-fix agent dispatch for errors the agent cannot fix via lint rules.

## Open questions

- Is the lint-fix agent for pyright errors currently succeeding consistently, or does it sometimes fail and fall through to `main-agent-edit`? If it rarely succeeds for pyright-specific errors, option 2 (fast-classify) is clearly the right path.
- Should `run_check_fix_loop` always flush a `STATUS=running` line at entry, regardless of which caller invokes it?

## Test plan
(no test plan section in plan-file)
