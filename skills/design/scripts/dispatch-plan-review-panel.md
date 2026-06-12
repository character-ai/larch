# dispatch-plan-review-panel.sh

**Purpose**: Renders static plan-review prompts (per-archetype vendor rows), appends dynamic slots from `$DESIGN_TMPDIR/scout-plan-manifest.json` (`dyn-cursor-plan-<slug>` / `dyn-codex-plan-<slug>`), and dispatches via `scripts/dispatch-with-waterfall.sh`.

**Codex round gating (#4062)**: Codex specialist and dynamic twin slots are emitted in round 1 whenever Codex is present; starting with round 2 they are emitted only as a replacement when Cursor is absent. When both vendors are present in round 2+, the panel emits Cursor specialists plus one generic Codex reviewer (`codex-plan-generic`). The `write_dynamic_prompt` vendor note still names Codex in that case because the generic Codex reviewer covers the static lenses. `--no-fallback` is passed to the waterfall only while Codex peer rows cover Cursor rows; in round 2+ with both vendors present, normal fallback stays enabled so a failed Cursor slot may backfill via Codex or Claude. Single-vendor and both-absent invocations keep their status-quo fallback behavior.

**Primary callers**: `skills/design/SKILL.md` Step 3.

Validates `$DESIGN_TMPDIR` via `larch_design_tmpdir_validate` after the required-arg check, before reading manifests under `$DESIGN_TMPDIR`.

**Environment override**: `DISPATCH_PLAN_REVIEW_WATERFALL_SH` may point to a stub `dispatch-with-waterfall.sh` for harnesses.

**Both externals absent**: launches a single combined Claude reviewer (`claude-plan-generic-output.txt`), writes one manifest row for that reviewer, runs `validate-research-output.sh --structured-reviewer-mode --write-structured` to materialize the structured sidecar, and emits `PANEL_PATHS_FILE` plus `DEGRADED_ROUND` from dispatch outcome. When the generic reviewer's output fails the first-line format gate (`_generic_first_line_ere`) or passes the gate but fails structured validation, the path is kept but the round stays degraded and a `WARN=plan-review-panel: generic Claude reviewer …` line names the format-gate miss so it is distinguishable from an empty/failed reviewer (#3392).

**Extra stdout KVs** (after the waterfall block): `DYNAMIC_SLOT_COUNT`, `DEGRADED_ROUND` (`true` when `STATIC_DISPATCH_OK=false`, `COMBINED_FALLBACK_COUNT > floor(slot_count/2)`, the paths-file lists fewer succeeded slots than the manifest, or `ALL_SLOTS_DROPPED=true`), `PANEL_PATHS_FILE` (same role as `ALL_OUTPUT_FILES_PATH`).

The script passes through waterfall dispatcher KVs including `FALLBACK_COUNT`, `COMBINED_FALLBACK_COUNT`, `ALL_SLOTS_DROPPED`, `DROPPED_SLOTS_FILE` (the per-slot drop sidecar from `dispatch-with-waterfall.sh`; `plan-review-loop.sh` consumes it to log per-slot drop reasons, #3392), and `WARN=cost-fallback-exceeded-threshold` when emitted upstream. Under `--no-fallback`, partial success is expressed via the compact paths-file and `DEGRADED_ROUND`; there is no phase-2 relaunch or `PHASE2_RELAUNCH_COUNT` metering.

**Harness**: `skills/design/scripts/test-dispatch-plan-review-panel.sh`.

**Edit in sync**: this file, `dispatch-plan-review-panel.sh`, `skills/design/scripts/test-dispatch-plan-review-panel.sh`, `scripts/test-design-structure.sh`, `skills/shared/topology.tsv`.

## Feature/scope anchor forwarding

`--feature-file` is the staged scope anchor under `$DESIGN_TMPDIR`, not brainstorm-merged context. The dispatcher forwards it into static role renders, the generic fallback render, and the shared prompt tail used by dynamic slots. No baseline file is forwarded.

## Conditional reviewer pruning

`--prune-round-num N --prune-ledger FILE` enables `scripts/reviewer-prune.sh filter` after `plan-review-slots.ndjson` is fully built and before the waterfall dispatch. When rows are removed, the unfiltered manifest is copied to `plan-review-slots.pre-prune.ndjson` and the canonical `plan-review-slots.ndjson` is atomically replaced, so degradation math and downstream mapping use filtered counts. If the filtered manifest is empty, the dispatcher emits success KVs with `PANEL_PRUNED_EMPTY=true`, zero dynamic slots, `DEGRADED_ROUND=false`, an empty `PANEL_PATHS_FILE`, and exits before the waterfall. The both-externals-absent generic Claude path writes one `plan-review-slots.ndjson` row (`slot=claude-plan-generic`, `tool=claude_sub`) before emitting `PANEL_PATHS_FILE`; it is not pruned.

## Concise prune/log audit update

`--round-num` selects the artifact directory under `plan-review/round-N/`; `--prune-round-num` remains the reviewer-prune filter counter. Dispatch writes `prune-decision.env` before every exit and emits the same prune KV tuple on stdout.

Fallback Claude reviewer slots use `claude-sonnet-4-6`; these are both-externals-down backups and intentionally stay on the cheaper Sonnet model rather than the Fable voter/drafter model.
