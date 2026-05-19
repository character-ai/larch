# dispatch-panel.sh Contract

`skills/review/scripts/dispatch-panel.sh` plans and launches `/review` reviewer slots.

It dispatches all reviewer slots through `scripts/dispatch-with-waterfall.sh`, which applies a three-phase waterfall fallback per slot: Phase 1 uses the primary tool (Cursor or Codex) when present; Phase 2 tries the alternate external tool when Phase 1 fails or is absent; Phase 3 launches a Claude subprocess reviewer when both external phases fail or are absent. This means reviewer slots always produce output — Claude fills any slot that cannot be covered by an external tool.

**Simple panel** (`--panel simple`): 6 Cursor specialist slots (structure, correctness, testing, security, edge-cases, plan-fidelity) + 1 Codex generalist slot using `agents/code-reviewer.md`. Total 7 slots when both tools are healthy. Plan file is required and always passed to all slots; absence is a hard fail (exit 2).

**Hard panel** (`--panel hard`): 6 Cursor specialist slots + 6 Codex specialist slots (structure, correctness, testing, security, edge-cases, plan-fidelity each). Total 12 slots when both tools are healthy. Plan file is required; absence is a hard fail (exit 2).

Both panels always include plan-fidelity; there is no longer a conditional based on plan file presence.

Dynamic archetypes are opt-in with `--dynamic-archetypes N` or `LARCH_DYNAMIC_ARCHETYPES_MAX`, where `N` must be `0..4`; the flag overrides the env var and the default is `0`. An explicitly empty `LARCH_DYNAMIC_ARCHETYPES_MAX` is invalid and exits 2. When enabled, `dispatch-panel.sh` invokes `scripts/scout-dynamic-archetypes.sh` once per review round via `$REVIEW_TMPDIR/scout-round<round>-manifest.json`, persists the authoritative scout result in `$REVIEW_TMPDIR/scout-round<round>-status.env`, then appends valid scout archetypes as Cursor-primary `prompt_file` slots with normal waterfall fallback. Dynamic agent files are synthesized under `$REVIEW_TMPDIR/dynamic-archetypes/` and are ephemeral; they bypass `agent-sync`. In diff mode, docs-only, test-only, and generated-only diffs skip the scout and emit `SCOUT_STATUS=skipped-<mode>`. If the round manifest already exists but the companion status env is missing, the dispatcher fails closed with `SCOUT_STATUS=parse-failed` and rewrites the manifest to empty whenever the cached manifest is not a **valid** scout JSON with `archetypes` length `0` (non-empty or schema-invalid manifests are treated as stale). A valid empty manifest alone is recovered as `SCOUT_STATUS=empty` (no rewrite). If diff mode loses its diff file before scout launch, the dispatcher writes an empty manifest and emits `SCOUT_STATUS=missing-diff-file` as a soft failure. Scout parse failures may also emit `SCOUT_FAIL_REASON`; when `SCOUT_STATUS=parse-failed`, the dispatcher always writes a local diagnostic sidecar at `$REVIEW_TMPDIR/scout-parse-failed-round<N>-diag.txt`, then — unless `REVIEW_TMPDIR` or the manifest path is under a test harness ancestor (matching `test-dispatch-panel.*`, `test-review-core.*`, or `test-scout-*`) — appends a `Warnings` entry to the resolved execution-issues log (`LARCH_EXECUTION_ISSUES_LOG`, then `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`, then `$IMPLEMENT_TMPDIR/execution-issues.md`, then `$REVIEW_TMPDIR/execution-issues.md`). The test-harness path guard prevents test fixtures from leaking diagnostic entries into a parent `/implement` run's committed execution-issues log. If the append helper fails, the dispatcher emits a `WARN=` line instead of failing silently.

Scout output is treated as untrusted metadata. The dispatcher does not forward LLM-authored `prompt_body` as trusted reviewer instructions; instead it synthesizes a fixed reviewer template and quotes the scout rationale/prompt text inside an untrusted data block for context only.

Once-per-round-dispatch is scoped to `$REVIEW_TMPDIR`. Standalone `/review` reuses the sentinel for the run; `/implement` creates a new round dir after fixes, so the scout can run again against the changed diff in the next round.

`PANEL_MODE=waterfall` is always emitted (the waterfall is the only dispatch mode). `PANEL_SHAPE=simple|hard` reports the selected topology shape. `DISPATCH_OK=false` is emitted when any Phase 3 Claude slot fails, so callers can gate on full-panel availability. `WARN=cost-fallback-exceeded-threshold` is emitted when the Phase 3 fallback count exceeds `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD`.

Pass `--description-text` to thread the user's description through to both external and Claude reviewer prompts in description mode.

Pass `--competition-notice-file <path>` to enable competition scoring language and append the file contents to all external reviewer prompts via the waterfall launch path.

Pass `--session-env-path` in nested `/implement` runs. `SESSION_ENV_PATH` is exported after argument parsing so `launch-review.sh` subprocesses inherit it; `timing-ledger.sh record-vendor-task` resolves the per-run timing ledger via the `SESSION_ENV_PATH` fallback, enabling Vendor Task Averages in timing reports.

Use `--launch-review <path>` in harnesses to override the external reviewer launcher. The default remains `${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh`.

Stdout is `KEY=value` only: `EXTERNAL_OUTPUT_FILES`, `CLAUDE_OUTPUT_FILES`, `PANEL_MODE`, `PANEL_SHAPE`, `SCOUT_STATUS`, optional `SCOUT_FAIL_REASON`, `DYNAMIC_SLOTS`, `STATIC_SLOT_COUNT`, `SLOT_COUNT`, `PANEL_MANIFEST`, `DISPATCH_OK`, optional `SCOUT_MANIFEST`, and optional `WARN`. `SLOT_COUNT` is total static plus dynamic slots; `STATIC_SLOT_COUNT` preserves the pre-scout panel size.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-dispatch-panel.sh`, wired through `make test-dispatch-panel`.
