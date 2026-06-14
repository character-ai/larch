# design-step5c.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Writes `$DESIGN_TMPDIR/.bg-wait-active` after publish preconditions and pause-save checks, then removes it on exit so hook enforcement covers publish/result parsing.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Parses `design-publish.sh` exit `0` from `.design-publish-result.env` first with stdout fallback.
- Forces stdout authority for exit `1`, `3`, and `4` by using a guaranteed-absent primary result env. This prevents stale primary success data from masking current plan-write failures, result-env write failures, or validator defects.
- Aborts before normal result parsing for exit `2` and unexpected non-zero exits.
- Emits non-empty `final-summary.md` between `LARCH_FINAL_SUMMARY_BEGIN` and `LARCH_FINAL_SUMMARY_END` markers on normal publish handoff and failed publish-tail staging.
- Does not emit stale final-summary markers for validator rc `4`.
- Does not replace `REPORT_GATE_SIDECARS_FILE`; sidecars remain a path handoff after marked summary output.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
