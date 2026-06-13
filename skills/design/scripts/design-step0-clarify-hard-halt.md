# design-step0-clarify-hard-halt.sh

## Purpose

Mechanical Step 0b helper for clarify-loop exhaustion or unrecovered clarify helper failure. Stages `failed-clarify` terminal state before the Final summary block.

## Primary callers

- `skills/design/SKILL.md` Step 0b clarify hard-halt branch

## Invariants

- Canonicalizes `$DESIGN_TMPDIR` before staging and failure-detail paths.
- Invokes `design-stage-terminal-state.sh` with clarify-loop tokens and exports `SUMMARY_OUTCOME=failed-clarify` whether staging succeeds or fails closed.
- Optional flags: `--exit-code`, `--failure-detail-log`.

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-failure-report.sh`, and `skills/design/scripts/test-design-stage-terminal-state.sh`.
