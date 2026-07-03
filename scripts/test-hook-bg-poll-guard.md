# test-hook-bg-poll-guard.sh

## Purpose

Offline regression harness for `scripts/hook-bg-poll-guard.sh`.

## Primary callers

- `Makefile` target `test-hook-bg-poll-guard`.

## Invariants

- Exercises the shipped `hooks/hooks.json` registration and the guard's allow, deny, fail-open, stale-marker, wrapper-routed, Step 3 recovery-waiter, foreground terminal-sentinel probe, and telemetry paths.
- Covers `.completed/step-3-terminal` recovery-waiter denial across the bare, braced `${DESIGN_TMPDIR}`, and `DESIGN_TMPDIR=<abs>;`-prefixed forms (#4725, flipped from allow); the co-located foreground-probe replacement that stays allowed; appended-probe denial; and continued `.step3-review-result.env` waiter denial.
- Covers live-marker foreground probes where terminal sentinels are absent and the expected result is `WAIT`; for `/implement` Step 3/5, covers the exact `test -f` same-step probe carve-out and clamp.
- Pins symlink denial, non-terminal `step-3` / `step-5c` denial, result-env denial, sleep-loop denial, and appended `cat` / `ls` / `stat` / `jq` denial.
- Covers the #5610 compound-probe bypass shape: one command referencing both a `tasks/*.output` file and `.completed/step-3-terminal` denies while a live marker exists, exercising the generic `bash_has_probe_verb` + `bash_has_probe_target` deny path rather than the simple foreground-probe clamp (which excludes `tasks/*.output`).
- Pins the Step 5c release split: `.completed/step-5c` does not release the marker, and `.completed/step-5c-terminal` does.
- Covers marker denial, terminal-sentinel release, and symlink-sentinel refusal for `design-step4-tail`, `implement-step5-resume`, `implement-step5-self-review`, `implement-step6-checks`, and `implement-step7a`; those implement steps do not gain the Step 3/5 foreground-probe carve-out.
- Pins the Step 4 foreground probe carve-out for `.completed/step-4`, including repeated-probe clamp behavior and denial of non-Step-4 terminal probes while the Step 4 tail marker is live.
- Covers the #5925/#6080 cross-session fix: a live marker belonging to an unrelated repo clone (different embedded clone tag) does not deny a bare `$IMPLEMENT_TMPDIR`/`$DESIGN_TMPDIR` reference or Bash/Read `tasks/*.output` read from a different clone's cwd, a marker whose embedded clone tag matches the probing cwd's basename still denies (including hyphenated clone tags and both the `IMPLEMENT_TMPDIR` and `DESIGN_TMPDIR` shapes), and an empty/missing `cwd` fails open rather than denying.
- Uses a temporary marker path supplied through `LARCH_BG_POLL_GUARD_MARKER`; it does not depend on a real Claude Code session.

## Harness

Run with `bash scripts/test-hook-bg-poll-guard.sh`.
