# design-step3-entry.sh

## Purpose

Combines adjacent `/design` script-call blocks so `skills/design/SKILL.md` keeps a single Bash call across this prompt-side boundary.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- `skills/design/SKILL.md` MANDATORY READs `plan-review-runtime.md` before invoking this wrapper.

- Forwards `--session-env-path` and `--claude-pid` to the internal Python entry points.
- Accepts `--reentry` for Gate A / Gate C routed review re-entry, writes `$DESIGN_TMPDIR/.step3-reentry`, and clears `$DESIGN_TMPDIR/oos-aggregate-pool.md` after validating `DESIGN_TMPDIR`.
- `--reentry` does not clear `$DESIGN_TMPDIR/.step3-entry-plan-printed`; the continuation entry point owns that cleanup.
- Keeps the combined entry order: clear `.pause-save-complete`, call `python/cli.py plan-review step3-entry-state`, exit on `.pause-save-complete`, then materialize the scope anchor and call `python/cli.py plan-review step3-entry-preview`. The runtime slice owns the preview contract.
- Materializes and validates `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` before the Step 3 review launch can be scheduled. The anchor uses the issue title plus `issue-body.txt` with any prior `larch:plan` block stripped, falling back to `feature-description.txt` or a verbal prompt when needed, and appends an approved outline when present.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `make test-design-structure` and `python/test_design_pause.py`.
