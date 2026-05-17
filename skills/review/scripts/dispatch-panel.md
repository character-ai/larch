# dispatch-panel.sh Contract

`skills/review/scripts/dispatch-panel.sh` plans and launches `/review` reviewer slots.

It dispatches all reviewer slots through `scripts/dispatch-with-waterfall.sh`, which applies a three-phase waterfall fallback per slot: Phase 1 uses the primary tool (Cursor or Codex) when present; Phase 2 tries the alternate external tool when Phase 1 fails or is absent; Phase 3 launches a Claude subprocess reviewer when both external phases fail or are absent. This means reviewer slots always produce output — Claude fills any slot that cannot be covered by an external tool.

**Simple panel** (`--panel simple`): 6 Cursor specialist slots (structure, correctness, testing, security, edge-cases, plan-fidelity) + 1 Codex generalist slot using `agents/code-reviewer.md`. Total 7 slots when both tools are healthy. Plan file is required and always passed to all slots; absence is a hard fail (exit 2).

**Hard panel** (`--panel hard`): 6 Cursor specialist slots + 6 Codex specialist slots (structure, correctness, testing, security, edge-cases, plan-fidelity each). Total 12 slots when both tools are healthy. Plan file is required; absence is a hard fail (exit 2).

Both panels always include plan-fidelity; there is no longer a conditional based on plan file presence.

`PANEL_MODE=waterfall` is always emitted (the waterfall is the only dispatch mode). `PANEL_SHAPE=simple|hard` reports the selected topology shape. `DISPATCH_OK=false` is emitted when any Phase 3 Claude slot fails, so callers can gate on full-panel availability. `WARN=cost-fallback-exceeded-threshold` is emitted when the Phase 3 fallback count exceeds `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD`.

Pass `--description-text` to thread the user's description through to both external and Claude reviewer prompts in description mode.

Pass `--competition-notice-file <path>` to enable competition scoring language and append the file contents to all external reviewer prompts via the waterfall launch path.

Pass `--session-env-path` in nested `/implement` runs. `SESSION_ENV_PATH` is exported after argument parsing so `launch-review.sh` subprocesses inherit it; `timing-ledger.sh record-vendor-task` resolves the per-run timing ledger via the `SESSION_ENV_PATH` fallback, enabling Vendor Task Averages in timing reports.

Use `--launch-review <path>` in harnesses to override the external reviewer launcher. The default remains `${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh`.

Stdout is `KEY=value` only: `EXTERNAL_OUTPUT_FILES`, `CLAUDE_OUTPUT_FILES`, `PANEL_MODE`, `PANEL_SHAPE`, `SLOT_COUNT`, `PANEL_MANIFEST`, `DISPATCH_OK`, and optionally `WARN`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-dispatch-panel.sh`, wired through `make test-dispatch-panel`.
