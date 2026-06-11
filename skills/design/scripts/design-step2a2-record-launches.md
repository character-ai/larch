# design-step2a2-record-launches.sh

## Purpose

Records launched sketch slot output paths in `$DESIGN_TMPDIR/sketch-launched-paths.txt` before Step 2a.2 parallel launches.

## Primary callers

- `skills/design/SKILL.md` Step 2a.2

## Invariants

- Accepts `--mode regular|quick` and uses the same availability rules as `references/sketch-launch.md`.
- Writes only slots that will actually be launched; skipped unavailable tools are omitted.
- `design-step2a3-collect.sh` reads this sidecar and does not infer paths from availability flags.

## Harness

Covered by `scripts/test-design-structure.sh`.
