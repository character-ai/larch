# decompose-panel-dispatch.sh

**Purpose**: render eight decomposition prompts (four archetypes × Cursor/Codex) and invoke `scripts/dispatch-with-waterfall.sh` in `description` mode.

**Primary caller**: `/design` Step 2b.5 Split-path (orchestrator loads `skills/design/references/decompose-panel.md` first).

**CLI**: `--design-tmpdir DIR --codex-present true|false --cursor-present true|false --mode plan|feature-only [--plan-file PATH] [--feature-file PATH] [--discussion-round1-file PATH] [--timeout SEC]`. In `plan` mode, `--plan-file` is required. In `feature-only` mode, `--feature-file` is required. When `--feature-file` is omitted in `plan` mode, the helper defaults to `$DESIGN_TMPDIR/feature-description.txt`.

**Stdout**: forwards the waterfall dispatcher KVs and appends `PANEL_OUTPUTS_FILE`, `DEGRADED_PANEL`, and `PANEL_STATUS`.

**Harness override**: `DECOMPOSE_PANEL_WATERFALL_SH` — path to a stub `dispatch-with-waterfall.sh` for offline tests (`skills/design/scripts/test-decompose-panel-dispatch.sh`).
