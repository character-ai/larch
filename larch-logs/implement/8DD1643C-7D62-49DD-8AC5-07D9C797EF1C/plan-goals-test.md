## Goal
Implement issue #5868: [IMPLEMENTING] [BUG] hook-no-progress-guard and hook-bg-poll-guard TMPDIR scan times out under….

## Implementation Plan
## Summary

`hook-no-progress-guard.sh` times out when called as the `UserPromptSubmit` hook because its `marker_candidates()` function runs `find "${TMPDIR:-/tmp}" -maxdepth 3 -name .bg-wait-active -type f`, which on macOS scans ~77,000–84,000 directories under the per-user TMPDIR (`/var/folders/.../T/`). Under concurrent load (e.g., parallel `/implement` sessions), this find can take 5 seconds or more, exceeding the hook's 5-second timeout. `hook-bg-poll-guard.sh` has an identical `marker_candidates()` function and the same 5-second timeout, and fires on every `PreToolUse` (Read/Bash/Monitor/TaskOutput) event, so it is equally susceptible.

## Original report

UserPromptSubmit hook timed out after 5s — output discarded. Raise the hook's "timeout" to allow more time.

Observed when running `/release` in a repo that had concurrent larch `/implement` sessions running in a sibling worktree.

## Reproduction scenario

1. Have a macOS developer machine with a large TMPDIR accumulation (typical after days of active use: 77,000+ subdirs under `/var/folders/.../T/`).
2. Start two or more concurrent larch sessions (e.g., `/release` in one worktree and `/implement` in another), adding IO pressure on the shared macOS TMPDIR.
3. Submit any user prompt while the sessions are active.
4. Observe: `UserPromptSubmit hook timed out after 5s — output discarded.`

Without concurrent pressure, the same find takes ~0.9s real / ~4s sys on the same machine. Under load it can exceed 5s.

## Expected behavior

The hook completes within its timeout budget, finds any live `.bg-wait-active` markers, and allows the user prompt to proceed (or blocks it if a circuit breaker is armed).

## Observed behavior

The hook times out (5 seconds, per `hooks/hooks.json`). Claude Code discards the hook output and proceeds. The no-progress circuit-breaker check is silently skipped.

## Root cause analysis

`marker_candidates()` in `scripts/hook-no-progress-guard.sh` (line 62–73) runs two `find` calls unconditionally:

```bash
find "$HOME/.cache/larch/sessions" -maxdepth 2 -name .bg-wait-active -type f 2>/dev/null || true
find "${TMPDIR:-/tmp}" -maxdepth 3 -name .bg-wait-active -type f 2>/dev/null || true
```

On macOS, `$TMPDIR` resolves to `/var/folders/<hash>/T/`, a per-user temp directory shared by all processes on the machine. It accumulates directories over time without automatic cleanup. With 77,000+ directories at `maxdepth 1` and ~84,000 at `maxdepth 3`, the second `find` call consistently takes 0.9s–5s+ depending on system load and disk I/O contention.

The hook is registered with `"timeout": 5` in `hooks/hooks.json`. Under concurrent larch session load (multiple `/implement` or `/design` sessions), this threshold is regularly exceeded.

The identical `marker_candidates()` implementation exists in `scripts/hook-bg-poll-guard.sh` (line 48–58, TMPDIR scan at line 57), which fires on every `PreToolUse` event for Read/Bash/Monitor/TaskOutput — a much higher frequency than UserPromptSubmit.

## Evidence

- `hooks/hooks.json` (UserPromptSubmit): `hook-no-progress-guard.sh` registered with `"timeout": 5`.
- `hooks/hooks.json` (PreToolUse): `hook-bg-poll-guard.sh` registered with `"timeout": 5`.
- `hooks/hooks.json` (Stop): `hook-no-progress-guard.sh` also registered at Stop with `"timeout": 5`.
- `scripts/hook-no-progress-guard.sh:71`: `find "${TMPDIR:-/tmp}" -maxdepth 3 -name .bg-wait-active -type f`
- `scripts/hook-bg-poll-guard.sh:57`: same pattern.
- Live timing on affected machine: `find "${TMPDIR:-/tmp}" -maxdepth 3 -name .bg-wait-active -type f` → 0.94s real, 4.0s sys (77,242 dirs at depth 1, 83,846 at depth 3).
- Error message from failing run: `UserPromptSubmit hook timed out after 5s — output discarded. Raise the hook's "timeout" to allow more time.`

## Affected files

- `hooks/hooks.json` — timeout values for `hook-no-progress-guard.sh` (UserPromptSubmit, Stop) and `hook-bg-poll-guard.sh` (PreToolUse).
- `scripts/hook-no-progress-guard.sh` — `marker_candidates()` function with the wide TMPDIR scan.
- `scripts/hook-bg-poll-guard.sh` — identical `marker_candidates()` with the same TMPDIR scan.
- `scripts/hook-no-progress-guard.md` / `scripts/hook-bg-poll-guard.md` — docs to update alongside any script change.

## Suggested fix(es)

**Option A (immediate): Raise timeout.** Increase `"timeout"` from `5` to `10` for `hook-no-progress-guard.sh` in `hooks/hooks.json` (all three registrations: UserPromptSubmit, Stop, and PreToolUse for `hook-bg-poll-guard.sh`). This buys headroom without any script change. Risk: does not address the structural cause; a heavily loaded machine may still exceed 10s.

**Option B (structural): Scope the TMPDIR search.** Use a two-step find that first narrows to larch-prefixed dirs before scanning for the marker:

```bash
find "${TMPDIR:-/tmp}" -maxdepth 1 -name 'larch-*' -type d \
  -exec find {} -maxdepth 2 -name .bg-wait-active -type f \;
```

This requires that all larch session tmpdirs (those that host `.bg-wait-active`) be created with a `larch-` prefix (e.g., `mktemp -d "${TMPDIR:-/tmp}/larch-session-XXXXXX"`). If the session tmpdir naming is not already `larch-`-prefixed, that convention must be established first or a known prefix verified.

**Option C (belt-and-suspenders):** Apply both A and B. Raise the timeout to 10 and scope the search. The timeout increase protects existing deployments during the transition; the scoped search eliminates the structural issue.

## Open questions

- Are larch `/design` and `/implement` session tmpdirs already created with a `larch-` prefix under TMPDIR, or do they use generic `mktemp -d` (producing `tmp.XXXXXXXX` names)? The answer determines whether Option B is a one-line search change or requires a session-tmpdir naming convention change.
- Should the `$HOME/.cache/larch/sessions` path alone be sufficient? If all active sessions durably write markers there, the TMPDIR scan may be redundant (or serve only as a fallback for sessions whose health-cache write races with the hook). If so, removing the TMPDIR scan entirely is safe and cleanest.
- Does `hook-bg-poll-guard.sh` also need the same fix, or is its PreToolUse frequency low enough in practice that it has not yet timed out?

## Test plan
(no test plan section in plan-file)
