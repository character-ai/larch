# dispatch-plan-review-panel.sh

**Purpose**: Renders static plan-review prompts (10 slots), appends dynamic slots from `$DESIGN_TMPDIR/scout-plan-manifest.json` (`dyn-cursor-plan-<slug>` / `dyn-codex-plan-<slug>`), and dispatches via `scripts/dispatch-with-waterfall.sh` with `--no-fallback`.

**Primary callers**: `skills/design/SKILL.md` Step 3.

Validates `$DESIGN_TMPDIR` via `larch_design_tmpdir_validate` after the required-arg check, before reading manifests under `$DESIGN_TMPDIR`.

**Environment override**: `DISPATCH_PLAN_REVIEW_WATERFALL_SH` may point to a stub `dispatch-with-waterfall.sh` for harnesses.

**Both externals absent**: launches a single combined Claude reviewer (`claude-plan-generic-output.txt`), runs `validate-research-output.sh --structured-reviewer-mode --write-structured` to materialize the structured sidecar, and emits `PANEL_PATHS_FILE` plus `DEGRADED_ROUND` from dispatch outcome.

**Extra stdout KVs** (after the waterfall block): `DYNAMIC_SLOT_COUNT`, `DEGRADED_ROUND` (`true` when `STATIC_DISPATCH_OK=false`, `COMBINED_FALLBACK_COUNT > floor(slot_count/2)`, the paths-file lists fewer succeeded slots than the manifest, or `ALL_SLOTS_DROPPED=true`), `PANEL_PATHS_FILE` (same role as `ALL_OUTPUT_FILES_PATH`).

The script passes through waterfall dispatcher KVs including `FALLBACK_COUNT`, `COMBINED_FALLBACK_COUNT`, `ALL_SLOTS_DROPPED`, and `WARN=cost-fallback-exceeded-threshold` when emitted upstream. Under `--no-fallback`, partial success is expressed via the compact paths-file and `DEGRADED_ROUND`; there is no phase-2 relaunch or `PHASE2_RELAUNCH_COUNT` metering.

**Harness**: `skills/design/scripts/test-dispatch-plan-review-panel.sh`.

**Edit in sync**: this file, `dispatch-plan-review-panel.sh`, `skills/design/scripts/test-dispatch-plan-review-panel.sh`, `scripts/test-design-structure.sh`, `skills/shared/topology.tsv`.
