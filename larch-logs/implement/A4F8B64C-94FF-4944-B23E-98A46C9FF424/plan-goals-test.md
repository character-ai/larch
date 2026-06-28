## Goal
Implement issue #5684: [IMPLEMENTING] [BUG] [URGENT] hook-bg-poll-guard and hook-no-progress-guard silently fail in production due to CLAUDE_PID session-scoping never matching.

## Implementation Plan
## Summary

Both `hook-bg-poll-guard.sh` and `hook-no-progress-guard.sh` silently fail to engage in production because their CLAUDE_PID-based session scoping resolves to `$PPID` (the hook runner's parent PID) instead of the real Claude session PID, causing the `.bg-wait-active` marker to be rejected as "not mine" for every hook invocation. The result: all anti-spurious-notification protections (#5240, #5478, #5639) are completely bypassed in production, allowing the orchestrator to make O(N) Bash sentinel probes across N consecutive turns during a Step 3 immediate-background wait — burning O(N) context turns even when the model knowingly violates Anti-pattern #5.

## Original report

During a `/design` run, the orchestrator received 25+ spurious `<task-notification>` events while `design-step3-review.sh` was running. Despite SKILL.md Anti-pattern #5 ("on empty-output notification, call no tool, end turn silently") being clear and loaded, the orchestrator probed `.completed/step-3-terminal` with a Bash call on every notification. The `hook-bg-poll-guard.sh` and `hook-no-progress-guard.sh` guards — specifically designed to cap this behavior — did not fire once.

Root-cause analysis surfaced two separate failures:
1. Model compliance failure: the orchestrator violated the behavioral rule.
2. Code failure: both hook guards were completely non-functional, providing zero protection.

## Reproduction scenario

1. Start a `/design` run that reaches the Step 3 immediate-background panel launch.
2. While `design-step3-review.sh` is backgrounded (PID active, `.bg-wait-active` present with `CLAUDE_PID=<session_pid>`), issue consecutive Bash probes of the form:
   ```bash
   DESIGN_TMPDIR="$HOME/.cache/larch/sessions/<session>"
   [ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo "TERMINAL_PRESENT=true" || echo "TERMINAL_PRESENT=false"
   ```
3. Expected: `hook-bg-poll-guard.sh` denies after `LARCH_BG_POLL_GUARD_PROBE_THRESHOLD` (2) consecutive probes; `hook-no-progress-guard.sh` blocks after 5 no-progress turns.
4. Observed: both hooks exit 0 (allow) on every probe. No denial is ever emitted.

## Expected behavior

- `hook-bg-poll-guard.sh` should deny the third consecutive terminal-sentinel foreground probe and emit: `"Repeated foreground terminal-sentinel probes while the sentinel is still absent..."`.
- `hook-no-progress-guard.sh` should arm the circuit breaker after 5 consecutive no-progress turns and block the next prompt.

## Observed behavior

Both hooks exit 0 on every invocation. The orchestrator made 25+ consecutive Bash probes without a single denial. The `bg-poll-guard-probe-denials.*.count` and `bg-poll-guard-denials.count` files were never created in the session tmpdir.

## Root cause analysis

Both hooks resolve `HOOK_CLAUDE_PID` identically:

```bash
# hook-bg-poll-guard.sh line 22, hook-no-progress-guard.sh line 51
HOOK_CLAUDE_PID="${LARCH_BG_POLL_GUARD_SESSION_PID:-${PPID:-}}"
_input_claude_pid=$(printf '%s' "$INPUT" | jq -r '.claude_pid // .parent_pid // ""' 2>/dev/null)
if [ -n "$_input_claude_pid" ] && [ "$_input_claude_pid" != "null" ]; then
  HOOK_CLAUDE_PID="$_input_claude_pid"
fi
```

In production there are two problems:

**Problem A — `LARCH_BG_POLL_GUARD_SESSION_PID` is never set.** `hooks/hooks.json` registers both hooks with no environment injection. Neither hook nor the plugin install mechanism ever sets this variable in the hook execution environment. It is only set in test harnesses (`test-hook-bg-poll-guard.sh`, `test-hook-no-progress-guard.sh`), creating a test/production divergence.

**Problem B — Claude Code PreToolUse / Stop / UserPromptSubmit hook input does not include `claude_pid` or `parent_pid`.** The fallback `${PPID:-}` resolves to the PID of the bash subprocess that runs the hook script. This is a transient kernel-assigned PID, entirely unrelated to the Claude session PID stored in `.bg-wait-active` (e.g., 58341).

The `marker_is_live` function then rejects the marker:

```bash
if [ -n "$stored_claude_pid" ] && [ -n "$hook_claude_pid" ] && [ "$stored_claude_pid" != "$hook_claude_pid" ]; then
  return 1   # marker treated as not ours; live_dirs_file stays empty
fi
```

Because `$PPID` (e.g., 62104) ≠ stored CLAUDE_PID (58341), the marker is never considered live. `live_dirs_file` is empty. The hook exits 0 at `[ -s "$live_dirs_file" ] || exit 0`.

All downstream logic — probe clamp, denial counter, no-progress counter, circuit breaker — is unreachable.

## Evidence

- `.bg-wait-active` contents confirmed `CLAUDE_PID=58341`; the hook's `$PPID` was not 58341.
- 25 consecutive Bash probes succeeded without any hook denial.
- `bg-poll-guard-probe-denials.*.count` and `bg-poll-guard-denials.count` were never created in `$DESIGN_TMPDIR`.
- `LARCH_BG_POLL_GUARD_SESSION_PID` appears in `test-hook-bg-poll-guard.sh` (set to `$$`) and `test-hook-no-progress-guard.sh` (set to `$$`), but nowhere in `hooks/hooks.json` or any production launcher path.
- `hooks/hooks.json` hook entries for both guards have no `env` or environment-injection field.
- Claude Code hook input is read via `jq -r '.claude_pid // .parent_pid // ""'` but the real input does not carry these fields (evidenced by fallback to `$PPID`).

## Affected files

- `scripts/hook-bg-poll-guard.sh` — CLAUDE_PID resolution is production-broken (lines 22–26); all denial logic is unreachable.
- `scripts/hook-no-progress-guard.sh` — same CLAUDE_PID resolution bug (lines 51–55); no-progress counter never increments.
- `hooks/hooks.json` — no environment injection for `LARCH_BG_POLL_GUARD_SESSION_PID`.
- `skills/design/SKILL.md` — Anti-pattern #5 and design-background-wait.md correctly describe the behavioral rule, but the claimed code enforcement does not exist in production.
- `docs/workflow-lifecycle.md` / `skills/shared/design-background-wait.md` — documentation references the no-progress circuit breaker as a live protection.

## Suggested fix(es)

**Option A (preferred — remove unreliable session scoping):** Drop the CLAUDE_PID check from `marker_is_live` in both hooks. Rely instead on: (1) the subprocess PID liveness check (`kill -0 "$pid"`) which already exists, (2) the marker age/timeout, and (3) the fact that each Claude session has its own isolated session tmpdir under `~/.cache/larch/sessions/`. Session isolation is provided by the tmpdir path, not by CLAUDE_PID matching. The CLAUDE_PID check adds no protection in practice and breaks all guards.

**Option B — inject the session PID via the marker path contract.** When `python/cli.py` or the launcher writes `.bg-wait-active`, it already knows the Claude session PID (`$PPID` from the session env). If `hooks.json` supported environment injection, `LARCH_BG_POLL_GUARD_SESSION_PID` could be set to the session PID at hook-invocation time. However, this requires Claude Code to support per-hook environment variables, which it may not.

**Option C — use `claude_pid` from hook input.** File a feature request or confirm whether Claude Code does pass `claude_pid` in PreToolUse/Stop/UserPromptSubmit payloads. If it does, debug why `jq -r '.claude_pid // .parent_pid // ""'` is returning empty.

Whichever fix is chosen, add a regression test that confirms the hook correctly denies probes when `.bg-wait-active` is present and the stored subprocess PID is alive, without relying on `LARCH_BG_POLL_GUARD_SESSION_PID`.

## Open questions

- Does Claude Code include `claude_pid` or a stable session identifier in PreToolUse / Stop / UserPromptSubmit hook payloads? If yes, what is the exact field name?
- Was Option A (removing CLAUDE_PID check) explicitly rejected previously? If so, what was the multi-session collision scenario that motivated the check, and does it apply given session-isolated tmpdirs?
- Does the test harness in `test-hook-bg-poll-guard.sh` cover the production code path (hook invoked by Claude Code with no `LARCH_BG_POLL_GUARD_SESSION_PID`)? If not, the tests give false confidence.

## Test plan
(no test plan section in plan-file)
