# dispatch-plan-review-panel.sh

**Purpose**: Renders static plan-review prompts (10 slots), appends dynamic slots from `$DESIGN_TMPDIR/scout-plan-manifest.json` (`dyn-cursor-plan-<slug>` / `dyn-codex-plan-<slug>`), and dispatches via `scripts/dispatch-with-waterfall.sh`.

**Primary callers**: `skills/design/SKILL.md` Step 3.

**Environment override**: `DISPATCH_PLAN_REVIEW_WATERFALL_SH` may point to a stub `dispatch-with-waterfall.sh` for harnesses.

**Extra stdout KVs** (after the waterfall block): `DYNAMIC_SLOT_COUNT`, `DEGRADED_ROUND` (`true` when `STATIC_DISPATCH_OK=false` or `FALLBACK_COUNT > floor(slot_count/2)`), `PANEL_PATHS_FILE` (same role as `ALL_OUTPUT_FILES_PATH`).
The script also passes through the waterfall dispatcher KVs, including `FALLBACK_COUNT`, `PHASE2_RELAUNCH_COUNT`, and `WARN=cost-fallback-exceeded-threshold`.
That `WARN` key inherits the upstream combined metering rule from `scripts/dispatch-with-waterfall.sh`: phase-3 Claude fallbacks plus grouped phase-2 relaunches are counted against `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD`.

**Harness**: `skills/design/scripts/test-dispatch-plan-review-panel.sh`.

**Edit in sync**: this file, `dispatch-plan-review-panel.sh`, `skills/design/scripts/test-dispatch-plan-review-panel.sh`, `scripts/test-design-structure.sh`, `skills/shared/topology.tsv`.
