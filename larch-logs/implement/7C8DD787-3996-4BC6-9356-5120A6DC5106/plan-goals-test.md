## Goal
Implement issue #5605: [IMPLEMENTING] [BUG] claude-ci lint-fix lane lacks fast-fail/auth-preflight: times out (exit 124) and stalls on degraded auth.

## Implementation Plan
## Scope decisions

- **Auth-fail action**: fast-fail early (detect degraded auth within ~60 s) but still escalate to the main agent — preserve the existing `lint-fix-main-agent-required` behavior.
- **Fix scope**: both `launch_claude_lint_fix_main` AND `launch_claude_ci_main`.

## Approach

Replace `subprocess.run(capture_output=True)` in `_run_claude_with_stdin` with a `Popen` + file-based stderr + polling loop. During the first `_CLAUDE_AUTH_FAST_FAIL_WINDOW` seconds, read the stderr file and match against `_CLAUDE_DEGRADED_AUTH_RE`; on match, terminate the child and return `EXIT_TIMEOUT` with the auth message in stderr so callers' existing `.diag` + `_AUTH_RE["claude"]` path classifies it as `health/auth`.

No changes to `checks.py` or escalation behavior.

## Files to modify/create

### UPDATED: python/larch/agents/agents.py

Add Claude degraded-auth detection.

- Add `_CLAUDE_AUTH_FAST_FAIL_WINDOW = 60.0`.
- Add `_CLAUDE_DEGRADED_AUTH_RE` matching:
  - `claude.ai connectors are disabled`
  - `apiKeyHelper failed`
  - `did not return a value`
  - auth-source precedence wording
- Extend `_AUTH_RE["claude"]` with the same patterns so existing `external_auth_verdict` classification returns `health/auth` instead of `other/timeout`.

Refactor `_run_claude_with_stdin`.

- Replace `subprocess.run(capture_output=True)` with `subprocess.Popen`.
- Use temp files for stdin and stderr to avoid pipe deadlock.
- Poll with `proc.wait(timeout=0.5)` until completion or timeout.
- During the first `_CLAUDE_AUTH_FAST_FAIL_WINDOW` seconds: read the stderr temp file; match `_CLAUDE_DEGRADED_AUTH_RE`; on match, terminate then kill the child; return `CommandResult(..., config.EXIT_TIMEOUT, stdout, stderr, elapsed)`.
- Preserve existing behavior for normal exit, full timeout, missing binary, and output decoding with replacement.
- Ensure the returned stderr contains the degraded-auth text so callers' `.diag` files classify as `health/auth`.

Keep callers unchanged — `launch_claude_ci_main`, `launch_claude_lint_fix_main`, and `launch_claude_subprocess_main` already write stderr to `.diag`, `.done`, timing, and launcher envelope from `CommandResult`.

### UPDATED: python/test_agents.py

Add regression coverage near the existing Claude CI and lint-fix tests.

- Add a direct auth-classification test: write sidecar text with the degraded-auth messages; assert `external_auth_verdict("claude", sidecar) == "auth"` and `classify_launch_failure(..., auth_verdict="auth", tool="claude")` yields `LaunchFailure("health", "auth")`.
- Add a Claude CI fast-fail test: fake `claude` binary writes degraded-auth to stderr then hangs; assert `.done=124`, `.diag` contains the auth text, `LAUNCHER_FAILURE_CLASS=health`, `LAUNCHER_FAILURE_REASON=auth`, and elapsed time is well below the requested timeout.
- Add a Claude lint-fix fast-fail test using the same fake-binary pattern.

## Edge cases

- Child exits before fast-fail window: preserve real exit code.
- Auth text appears after the fast-fail window: normal timeout path handles it.
- Empty stderr on timeout: keep fallback `"claude subprocess timed out"`.
- Termination fails: kill the child before returning.
- Large stderr: scan a bounded tail.

## Failure modes

- Too-broad regex → false auth classification: patterns are specific to observed messages.
- Popen deadlock if stdout piped and unread: use temp files for both stdout and stderr.
- Leaked sleeping child: always terminate, then kill after a short grace wait.
- New exit code changes downstream: keep `config.EXIT_TIMEOUT` (124).

## Testing strategy

- `python3 -m pytest python/test_agents.py -q -k 'launch_claude_ci or launch_claude_lint_fix or external_auth_verdict'`
- `make py-lint && make py-test`

diff_added: 150
diff_deleted: 25
mechanical_churn: false
diff_lines: 175

## Test plan
(no test plan section in plan-file)
