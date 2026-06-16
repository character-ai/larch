## Goal
Implement issue #4516: [IMPLEMENTING] design: design-step1d5.sh complete mode exits 1 on its final pause-check line.

## Implementation Plan
## Summary

`design-step1d5.sh --mode complete` exits 1 on the normal no-pause path because the `complete)` case's final statement is a bare `[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec ...` test. When no pause is pending the test returns 1, and as the script's last command under `set -euo pipefail` the wrapper exits 1. The `.completed/step-1d.5` sentinel is written on the prior line, so the failure is benign, but the orchestrator sees `Exit code 1` on every brainstorm-off run.

## Original report

Observed during `/design 4460`. Step 1d.5 `--mode complete` returned `Exit code 1` with no stdout. Inspection showed `.completed/step-1d.5` present and `.pause-requested` absent, so Step 1d.5 had completed functionally; the exit 1 came from the trailing pause-check.

## Reproduction scenario

1. Run `/design <issue>` with brainstorm off (the default; no `--brainstorm`).
2. At Step 1d.5, the orchestrator runs `design-step1d5.sh --mode complete`.
3. With no `.pause-requested` file present, the wrapper exits 1 even though it wrote `.completed/step-1d.5`.

## Expected behavior

`--mode complete` exits 0 after writing `.completed/step-1d.5` when no pause is pending (matching the `entry)` mode, which exits 0).

## Observed behavior

`--mode complete` exits 1. The sentinel is written correctly and forward progress is unaffected, but the non-zero exit is noisy and can be mistaken for a real failure.

## Root cause analysis

In the `complete)` case, the last statement is `[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec ... design pause-save`. With no pause file, `[ -f ... ]` returns 1; `exec` does not run; the `&&` list returns 1; and because it is the script's final command under `set -e`, the wrapper exits 1. The `entry)` case has the identical pause-check but is followed by a `... timing mark ... || true` line, so it exits 0. The trailing-test-as-last-line pattern is the bug.

## Evidence

- `skills/design/scripts/design-step1d5.sh:243-248` — the `complete)` case; line 247 is the final statement: `[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec ... design pause-save ...`.
- The `entry)` case (earlier in the same file) has the same pause-check but a subsequent `LARCH_TIMING_SKILL=design ... timing mark ... || true` line, so its final command returns 0.
- `set -euo pipefail` is set at the top of the wrapper (line 4).
- Live run: the Bash tool reported `Exit code 1` for the `--mode complete` fence; `.completed/step-1d.5` was present and `.pause-requested` absent.

## Affected files

- `skills/design/scripts/design-step1d5.sh` — the `complete)` case (line 247).

## Suggested fix(es)

- End the `complete)` pause-check arm with `|| true`, or add a trailing `exit 0` (or `:`) after line 247, mirroring how the `entry)` case stays at exit 0.
- Consider routing the pause-check through the existing `design_pause_check` helper (used by other wrappers) so a no-pause path always returns 0.
- Audit other wrapper `case` arms whose last statement is a bare `[ ... ] && exec ...` for the same trailing-test exit-code hazard.

## Open questions

- Do other `/design` wrapper modes share the trailing `[ ... ] && exec` last-statement pattern? A short audit could catch siblings before they surface as spurious non-zero exits.

## Test plan
(no test plan section in plan-file)
