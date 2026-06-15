# design-step-final-summary.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Writes `$DESIGN_TMPDIR/.bg-wait-active` around final summary rendering and removes it on exit so hook enforcement covers the immediate-background wait.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Called from an immediate-background Bash fence; callers wait for `<task-notification>` before marker extraction.
- Captures `render-final-summary.sh` stdout before emitting marked output.
- Emits non-empty `final-summary.md` between `LARCH_FINAL_SUMMARY_BEGIN` and `LARCH_FINAL_SUMMARY_END` markers for cancellation and terminal summary paths.
- Writes `$DESIGN_TMPDIR/.completed/step-final-summary` after marked output is ready so `hook-bg-poll-guard.sh` can release the immediate-background wait on terminal paths.
- Does not replace `REPORT_GATE_SIDECARS_FILE`; sidecars remain a path handoff after marked summary output.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
