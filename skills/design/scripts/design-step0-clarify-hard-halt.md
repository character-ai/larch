# design-step0-clarify-hard-halt.sh

## Purpose

Compatibility helper for clarify-loop exhaustion or unrecovered clarify helper
failure. Current Step 0b clarify routing uses `design-clarify.sh`; this helper is
retained for older in-flight runs and stages `failed-clarify` terminal state
before the Final summary block.

## Primary callers

- Older in-flight `/design` runs that still reference the former Step 0b
  clarify hard-halt branch

## Invariants

- Canonicalizes `$DESIGN_TMPDIR` before staging and failure-detail paths.
- Invokes `design-stage-terminal-state.sh` with clarify-loop tokens and exports `SUMMARY_OUTCOME=failed-clarify` whether staging succeeds or fails closed.
- Optional flags: `--exit-code`, `--failure-detail-log`.

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-failure-report.sh`, and `skills/design/scripts/test-design-stage-terminal-state.sh`.
