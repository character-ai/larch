# scripts/dispatch-with-waterfall.sh — contract

Three-phase per-slot fallback dispatcher for review-style fanout.

Input is an NDJSON slots file. Each row must contain:

- `slot`: stable slot label
- `tool`: primary external tool, `codex` or `cursor`
- `output`: phase-1 output path
- `agent` or `prompt_file`: source prompt for launchers

Rows may include optional metadata such as `weight` and `focus_area`; the dispatcher preserves validation compatibility and ignores those fields at launch time.

Phases:

1. Launch each slot on its assigned external tool when `--<tool>-present true`.
2. Failed or absent phase-1 slots launch on the other present external tool.
3. Remaining slots launch through `scripts/launch-claude-review.sh`.

Each phase is collected with `scripts/collect-agent-results.sh --summary-only`; `STATUS=OK` and `STATUS=cap_hit` settle a slot. Other statuses advance to the next phase, and a phase-3 failure leaves `DISPATCH_OK=false`.

Stdout keys:

- `PHASE1_SLOTS`, `PHASE2_SLOTS`, `PHASE3_SLOTS`
- `ALL_OUTPUT_FILES`
- `ALL_OUTPUT_TOOLS`
- `FALLBACK_COUNT`
- `WARN=cost-fallback-exceeded-threshold` when phase-3 count exceeds `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD` (default 3)
- `DISPATCH_OK=true|false`

Regression harness: `scripts/test-dispatch-with-waterfall.sh`.
