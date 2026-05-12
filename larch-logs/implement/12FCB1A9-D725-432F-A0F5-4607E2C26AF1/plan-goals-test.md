## Goal
Add a global LARCH_TIMING_LEDGER export to each of the three implementer test harnesses so that model-rejection and preflight tests do not bleed timing entries into the parent session's or global fallback ledger.

## Implementation Plan
Add `export LARCH_TIMING_LEDGER="$SCRATCH/timing-ledger.tsv"` immediately after each `trap 'rm -rf "$SCRATCH"' EXIT` line in:
- skills/implement/scripts/test-codex-implementer.sh
- skills/implement/scripts/test-cursor-implementer.sh (two SCRATCH scopes)
- skills/implement/scripts/test-gemini-implementer.sh

## Test plan
Run /relevant-checks and verify the export is present in all three files after trap lines.
