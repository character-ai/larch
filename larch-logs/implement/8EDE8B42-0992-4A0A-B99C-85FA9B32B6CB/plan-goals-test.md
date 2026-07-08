## Goal
Implement issue #6603: [IMPLEMENTING] [BUG] Codex policy-rejection sanitizer bypassed at 32KB tail boundary: truncated completed-command fragment raw-scans and can still false-kill.

## Implementation Plan
## Summary

PR #6599 (issue #6577) added `_sanitize_codex_events_for_policy_scan` so the policy-rejection scan ignores `aggregated_output` from successfully completed Codex commands. The 32KB tail bound is applied before sanitization. The window's first line is therefore usually a truncated JSON fragment. A truncated line fails `json.loads` and passes through raw. When the cut lands inside a completed command whose `aggregated_output` quotes historical policy-rejection diagnostics (the original #6577 repro: Codex grepping committed larch-logs), the raw fragment can satisfy both `_CODEX_EXEC_COMMAND_FAILED_RE` and `_CODEX_POLICY_BLOCKED_RE`. `_codex_policy_rejection_fast_fail` then kills a healthy process. The original bug re-opens whenever the quoted output is large.

## Code refs (main at c20110074)

- `python/larch/agents/_run_external.py:651`: `_CODEX_POLICY_REJECTION_TAIL_BYTES = 32768`.
- `python/larch/agents/_run_external.py:695`: `bounded = text[-_CODEX_POLICY_REJECTION_TAIL_BYTES:]`, then `scanned = _sanitize_codex_events_for_policy_scan(bounded)`. Bound first, sanitize second.
- `python/larch/agents/_run_external.py:676`: the sanitizer appends `json.JSONDecodeError` lines unchanged.
- `python/larch/agents/_run_external.py:757`: the streaming watcher maintains `new_tail = (tail + update.text)[-_CODEX_POLICY_REJECTION_TAIL_BYTES:]`. Once a completed-command event line is itself 32KB or larger, every subsequent watcher tick starts the window inside that line until 32KB of newer events accumulate. The exposure window is wide, not momentary.

## Reproduction scenario

1. A Codex reviewer or voter greps this repo. A successful command's `aggregated_output` quotes over 32KB of committed larch-logs diagnostics containing both "exec_command failed" and "blocked by policy" (or "Rejected(").
2. The event line for that completed command exceeds the 32KB tail, so the scan window starts mid-line.
3. The fragment is not valid JSON. It passes through the sanitizer unchanged. Both regex families match in `scanned`. The fast-kill fires on a healthy Codex slot with `FAILURE_CLASS=policy-rejection`.

## Expected behavior

Quoted output of successfully completed commands never triggers the kill, regardless of size. That was the goal of #6577.

## Observed behavior

Sanitization is effective only for complete JSON lines inside the window. The truncated head fragment raw-scans.

## Suggested fix

Either:

- After bounding, when `len(text) > _CODEX_POLICY_REJECTION_TAIL_BYTES`, drop the partial first line (for example `bounded.split("\n", 1)[1]` when a newline exists) so only complete lines are scanned. Genuine rejection events are small; losing one truncated line cannot hide them.
- Or sanitize line-wise on a complete-line stream before bounding.

Regression test: an events stream whose final completed-command event is a single JSON line over 32KB with `exit_code: 0` and trigger phrases inside `aggregated_output` must not trigger the kill; a genuine rejection event following it must still trigger.

## Severity

Same class as #6577: false kill of a healthy Codex slot. The phase2 vendor fallback mitigates, but the kill burns a slot and files an exec issue. Related: #6577 (PR #6599).

## Affected files

- `python/larch/agents/_run_external.py`
- `python/tests/agents/test_agents.py`

## Test plan
(no test plan section in plan-file)
