## Goal
Fix systematic missing Codex/Cursor token sections in token reports by capturing Codex stdout in the review sidecar and exporting IMPLEMENT_TMPDIR for proper session-id propagation.

## Implementation Plan
- `scripts/launch-review.sh`: redirect stdout+stderr to sidecar for Codex section (mirrors launch-codex-implement.sh)
- `skills/implement/SKILL.md`: export IMPLEMENT_TMPDIR in Step 0 alongside other env exports
- `scripts/test-launch-review.sh`: regression test — stdout-only stub + token-report.sh ### Codex assertion
- `scripts/launch-review.md`: document change

## Test plan
Run `make test-launch-review` / `/relevant-checks`. New regression test asserts `### Codex` appears in token-report output when stub writes to stdout only.
