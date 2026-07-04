# design-step3-entry.sh

## Purpose

Combines adjacent `/design` script-call blocks so `skills/design/SKILL.md` keeps a single Bash call across this prompt-side boundary.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Forwards `--session-env-path` and `--claude-pid` to the internal wrappers.
- Accepts `--reentry` for Gate A / Gate C routed review re-entry, writes `$DESIGN_TMPDIR/.step3-reentry`, and clears `$DESIGN_TMPDIR/oos-aggregate-pool.md` after validating `DESIGN_TMPDIR`.
- `--reentry` does not clear `$DESIGN_TMPDIR/.step3-entry-plan-printed`; legacy continuation preview cleanup belongs to `design-step3-continuation-entry.sh`.
- Keeps the combined entry order: clear `.pause-save-complete`, call `design-step3-entry-state.sh`, exit on `.pause-save-complete`, then call preview.
- Materializes and validates `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` before the Step 3 review launch can be scheduled. The anchor uses the issue title plus `issue-body.txt` with any prior `larch:plan` block stripped, falling back to `feature-description.txt` or a verbal prompt when needed, and appends an approved outline when present.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh` and `python/test_design_pause.py`.
