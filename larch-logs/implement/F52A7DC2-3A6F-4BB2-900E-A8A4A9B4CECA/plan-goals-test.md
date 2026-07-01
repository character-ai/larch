## Goal
Implement issue #5927: [IMPLEMENTING] [BUG] No-progress hook in one session blocks all larch clones.

## Implementation Plan
## Summary

A stale or slow `.bg-wait-active` marker in one larch session can arm `scripts/hook-no-progress-guard.sh` and block `UserPromptSubmit` in every Claude session using the larch plugin, including sessions in other larch clones.

Observed operator impact: all Claude sessions across `larch1` through `larch9` were blocked with:

```text
UserPromptSubmit operation blocked by hook:
No-progress circuit breaker: 8 consecutive turns detected under an active background-wait marker without real progress (threshold: 5 turns). The harness may be delivering spurious notifications (#5639).
```

The original blocked prompt was for an unrelated `/implement --merge 5880` takeover. The blocker came from an older `/design` run in `larch6`, so the guard crossed clone and task boundaries.

## Observed Evidence

Shared session cache contained multiple `.bg-wait-active` markers, but only one armed breaker:

```text
<TMPDIR>/no-progress-circuit-breaker-armed
```

The marker content was:

```text
PID=59700
CLAUDE_PID=63024
START_EPOCH=1782885099
STEP=design-step3-review
TIMEOUT_S=21600
```

The counter was:

```text
8
```

Process state showed the marker was not simply dead:

```text
59700 ... bash .../skills/design/scripts/design-step3-review.sh --session-env-path .../current-design-env-63024.sh --claude-pid 63024
59944 ... python .../python/cli.py plan-review run --design-tmpdir .../claude-design-larch6-_8s9eb1b --mode loop --new-process-group
40448 ... python .../python/cli.py plan-review voter-dispatch --ballot-file .../ballot.txt --design-tmpdir ... --codex-available true --cursor-available true
```

Recent tmpdir activity showed the task was still producing plan-review/voter artifacts after the breaker had armed. Clearing only these two files unblocked all sessions while preserving the live `.bg-wait-active` marker:

```text
no-progress-circuit-breaker-armed
no-progress-turns.count
```

## Root Cause Analysis

`hook-no-progress-guard.sh` uses global marker discovery:

```bash
find "$HOME/.cache/larch/sessions" -maxdepth 2 -name .bg-wait-active -type f
```

Then `UserPromptSubmit` blocks the next prompt if any live marker has `no-progress-circuit-breaker-armed`, regardless of which Claude session, clone, or workflow owns that marker.

The liveness check intentionally does not scope to `CLAUDE_PID`:

```bash
# #5684: liveness is NOT scoped by CLAUDE_PID.
```

That makes the guard a global kill switch for the entire larch plugin installation. It is useful for catching spurious notification loops, but the blast radius is too large. A slow-but-live background task in one clone can prevent unrelated sessions from receiving user prompts.

In this incident, the marker belonged to `claude-design-larch6-_8s9eb1b` and `STEP=design-step3-review`, while the blocked prompt was trying to continue `/implement --merge 5880` elsewhere. The hook had enough information to avoid this cross-session block, but the `UserPromptSubmit` path did not apply that scoping.

## Why This Is Bad

- One stalled or slow background wait in one clone blocks all larch clones.
- The operator cannot use another clone to investigate or recover without manually deleting sidecars.
- The error message says to clear the marker in "the session tmpdir", but it does not identify the offending tmpdir.
- Deleting `.bg-wait-active` is unsafe when the background process is still live; in this case the correct recovery was clearing only the no-progress sidecars.
- The hook can block unrelated tasks, e.g. an `/implement` prompt blocked by a `/design` marker from another clone.

## Suggested Fix

Constrain `UserPromptSubmit` blocking to the current Claude session or current repo/clone when that information is available.

Concrete options:

1. **Best fix: session-scoped blocker.** On `UserPromptSubmit`, compare the incoming Claude/session identity to marker metadata. Only block when the armed marker belongs to the current top-level Claude process or current session tmpdir.
2. **Fallback: repo-scoped blocker.** Add `REPO_ROOT` or clone tag to `.bg-wait-active`, then only block prompts from the same repo/clone. This would prevent `larch6` from blocking `larch9`.
3. **Safer global fallback.** If the hook cannot prove ownership, warn but do not block. Keep `Stop` counting global if needed, but make `UserPromptSubmit` fail open for foreign markers.
4. **Improve operator message.** Include the offending marker path, `STEP`, `PID`, `CLAUDE_PID`, age, and whether the terminal sentinel exists. Also recommend clearing `no-progress-circuit-breaker-armed` and `no-progress-turns.count` first when the process is live, instead of leading with `.bg-wait-active` deletion.
5. **Auto-recover on progress.** Reset no-progress sidecars when files under the marker tmpdir have changed since the last count, or when a known child dispatch process has started after the breaker armed. In this incident, newer plan-review/voter artifacts existed while the breaker remained armed.

## Acceptance Criteria

- A no-progress breaker armed in `larch6` does not block `UserPromptSubmit` in `larch1`, `larch2`, ..., `larch9`.
- A no-progress breaker armed by `/design` does not block an unrelated `/implement` session in another clone.
- The hook still blocks repeated no-progress turns in the owning session.
- The block message identifies the exact marker path and recovery files.
- Tests cover at least two markers from different session/clone identities and verify only the owning prompt is blocked.

## Workaround

If this happens before the fix ships:

1. Find the armed breaker:

```bash
find ~/.cache/larch/sessions -maxdepth 3 -name no-progress-circuit-breaker-armed -type f -print
```

2. Inspect the sibling `.bg-wait-active` and check whether its PID is still running.
3. If the process is live, clear only:

```bash
rm -f <session-tmpdir>/no-progress-circuit-breaker-armed <session-tmpdir>/no-progress-turns.count
```

4. Do not remove `.bg-wait-active` unless the background task is gone or the terminal sentinel is present.

## Test plan
(no test plan section in plan-file)
