# decompose-aggregator.sh

**Purpose**: concatenate eight panel outputs and run a **single-slot** `dispatch-with-waterfall.sh` merge pass that emits one Markdown partition (`## Recommendation` + `## Pieces`).

**Primary caller**: `/design` Split-path stage 0/1 per `skills/design/references/decompose-panel.md`.

**CLI**: `--design-tmpdir DIR --panel-outputs-file PATH --codex-present true|false --cursor-present true|false --output PATH [--timeout SEC]`.

**Stdout**: `AGGREGATOR_STATUS=ok|failed` and `AGGREGATOR_OUTPUT=<path>` via `emit_kv`.

**Primary tool**: the single-slot row is assigned to `codex` (more reliable than Cursor at returning structured output on the single safety-net slot); the shared dispatcher's `cursor → claude` fallback covers the remaining waterfall positions.

**Recommendation-heading gate**: the aggregator threads `--require-result-pattern '^[[:space:]]*## Recommendation'` into `dispatch-with-waterfall.sh` so narration-only "OK" outputs at the dispatcher boundary fall through to the next phase instead of settling silently. The post-call `grep -Eq '^[[:space:]]*## Recommendation'` on `AGGREGATOR_STATUS` is retained as defense-in-depth.

**Note**: `skills/review/scripts/aggregate-findings.sh` expects ### `FINDING_N` voting-shaped blocks; partition merges intentionally **do not** route through that script.

**Harness override**: `DECOMPOSE_AGGREGATE_WATERFALL_SH` — stub waterfall for offline tests (`skills/design/scripts/test-decompose-aggregator.sh`).
