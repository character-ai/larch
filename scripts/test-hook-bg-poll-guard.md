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
- Covers the #5925/#6080/#6108 cross-session fix: collection-time `.larch-keepalive` `CLONE_PATH` filtering drops known-foreign markers before Bash, Read, Monitor, TaskOutput, waiter, and foreground-probe clamp paths can deny. Foreign markers receive no denial or probe-clamp telemetry, while same-clone keepalive markers still deny from repo-root and repo-subdirectory cwds.
- Covers marker-local clone identity hardening: embedded `CLONE_PATH` wins over conflicting keepalive data, missing embedded identity falls back to keepalive, and fully unknown identity still fails safe for direct marker-dir probes.
- Pins the bare-dir-only Bash denial for same-clone marker dirs, including `/private` path aliases.
- Pins the fallback clone-tag heuristic when keepalive identity is unavailable, including hyphenated clone tags and both the `IMPLEMENT_TMPDIR` and `DESIGN_TMPDIR` shapes, and keeps empty/missing `cwd` fail-open behavior for bare tmpdir-variable references.
- Verifies `.bg-wait-active` diagnosis reads are allowed through both `Read` and simple Bash, while mixed marker-plus-progress-artifact commands still deny.
- Verifies every deny reason is valid JSON and includes `.bg-wait-active`, exact expected `STEP=...`, and `hook_version=...` metadata.
- Uses temporary marker paths supplied through both `LARCH_BG_POLL_GUARD_MARKER` and automatic session discovery; it does not depend on a real Claude Code session.

## Harness

Run with `bash scripts/test-hook-bg-poll-guard.sh`.
