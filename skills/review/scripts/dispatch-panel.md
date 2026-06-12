# dispatch-panel.sh Contract

`skills/review/scripts/dispatch-panel.sh` plans and launches `/review` reviewer slots.

It dispatches all reviewer slots through `scripts/dispatch-with-waterfall.sh`, which applies a three-phase waterfall fallback per slot: Phase 1 uses the primary tool (Cursor or Codex) when present; Phase 2 tries the alternate external tool when Phase 1 fails or is absent; Phase 3 launches a Claude subprocess reviewer when both external phases fail or are absent. This means reviewer slots always produce output — Claude fills any slot that cannot be covered by an external tool.

**Simple panel** (`--panel simple`) and **Hard panel** (`--panel hard`): both use the same static layout — active archetypes (`correctness`, `edge-cases`, `testing`) emitted once per available vendor. In round 1, when Cursor and Codex are both available, both are emitted per archetype and the waterfall is invoked with global `--no-fallback` so same-run peer rows are not duplicated by fallback. Starting with round 2, Codex specialist slots are suppressed while Cursor is available: only Cursor specialist slots are emitted, plus one generic Codex reviewer (`codex-generic` slot using `agents/code-reviewer.md`). The generic Codex slot participates in the reviewer pruning ledger like any static slot. When Cursor is unavailable in round 2+, Codex runs as the replacement specialist panel and the generic slot is not added (#4062). `--no-fallback` is applied only in round 1 with both vendors available; with one vendor available (or in round 2+ where Codex specialists are suppressed), the panel keeps normal fallback, so a Cursor slot that fails in round 2+ may backfill via Codex or Claude. When both vendors are down, Cursor-primary rows are emitted for Claude fallback. Plan file is required because `reviewer-testing` carries the folded plan-fidelity secondary scan; absence is a hard fail (exit 2).

Both panels always include `reviewer-testing`; there is no longer a conditional based on plan file presence.

Dynamic archetypes are opt-in with `--dynamic-archetypes N` or `LARCH_DYNAMIC_ARCHETYPES_MAX`, where `N` must be `0..3`; the flag overrides the env var and the default is `0`. An explicitly empty `LARCH_DYNAMIC_ARCHETYPES_MAX` is invalid and exits 2. When enabled without `--pre-scouted-manifest`, `dispatch-panel.sh` invokes `scripts/scout-dynamic-archetypes.sh` once per review round via `$REVIEW_TMPDIR/scout-round<round>-manifest.json`. When `--pre-scouted-manifest FILE` is supplied and no docs-only, test-only, generated-only, or dynamic-cap-zero skip applies, the file is normalized first with the existing cap, duplicate, reserved-slug, row-shape, and prompt-safety rules. A valid normalized pre-scouted manifest gets `SCOUT_STATUS=pre-scouted`, writes the per-round scout manifest, and uses the same dynamic slot synthesis as the successful scout path without launching `scripts/scout-dynamic-archetypes.sh`. A missing, empty, unparseable, fully filtered, or invalid supplied file writes an empty per-round manifest, emits `SCOUT_STATUS=parse-failed` with `SCOUT_FAIL_REASON=pre_scouted_manifest_validation`, continues static-only, and never falls through to the legacy scout. If `--pre-scouted-manifest` is absent, standalone `/review` behavior is unchanged. Existing docs-only, test-only, and generated-only skips take priority over both legacy scout launch and pre-scout synthesis, and `--dynamic-archetypes 0` disables dynamic slots even when a pre-scouted file is supplied.

Scout output is treated as untrusted metadata. The dispatcher does not forward LLM-authored `prompt_body` as trusted reviewer instructions; instead it synthesizes a fixed reviewer template and quotes the scout rationale/prompt text inside an untrusted data block for context only. The synthesized dynamic reviewer template instructs the model to begin the response with the literal `### In-Scope Findings` line (first character `#`), avoid Gathering/Checking/Reading/Looking-at-style process narration before that header, then emit `### Out-of-Scope Observations` after the last finding (or `NO_ISSUES_FOUND`). This aligns dynamic reviewer output grammar with the canonical `### In-Scope Findings` / `### Out-of-Scope Observations` format expected by `collect-findings.sh`.

Once-per-round-dispatch is scoped to `$REVIEW_TMPDIR`. Standalone `/review` reuses the sentinel for the run; `/implement` creates a new round dir after fixes, so the scout can run again against the changed diff in the next round.

`PANEL_MODE=waterfall` is always emitted (the waterfall is the only dispatch mode). `PANEL_SHAPE=simple|hard` reports the selected topology shape. `DISPATCH_OK=false` is emitted for true dispatcher exhaustion; dropped no-fallback peer rows are surfaced through `DROPPED_SLOTS_FILE` so `review-core.sh` can log them, count them in threshold math, and apply the per-archetype coverage gate. `WARN=cost-fallback-exceeded-threshold` is emitted when the combined phase-2 fall-through relaunch count plus the phase-3 Claude count exceeds `LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD`.

Pass `--description-text` to thread the user's description through to both external and Claude reviewer prompts in description mode.

Pass `--competition-notice-file <path>` to enable competition scoring language and append the file contents to all external reviewer prompts via the waterfall launch path.

Pass `--session-env-path` in nested `/implement` runs. `SESSION_ENV_PATH` is exported after argument parsing so `launch-review.sh` subprocesses inherit it; `python3 python/cli.py timing record-vendor-task` resolves the per-run timing ledger via the `SESSION_ENV_PATH` fallback, enabling Vendor Task Averages in timing reports.

Use `--launch-review <path>` in harnesses to override the external reviewer launcher. The default remains `${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh`.

Stdout is `KEY=value` only: `EXTERNAL_OUTPUT_FILES`, `CLAUDE_OUTPUT_FILES`, `PANEL_MODE`, `PANEL_SHAPE`, `SCOUT_STATUS`, optional `SCOUT_FAIL_REASON`, `DYNAMIC_SLOTS`, `STATIC_SLOT_COUNT`, `SLOT_COUNT`, `PANEL_MANIFEST`, `DISPATCH_OK`, optional `DROPPED_SLOTS_FILE`, optional `SCOUT_MANIFEST`, and optional `WARN`. `SLOT_COUNT` is total static plus dynamic slots; `STATIC_SLOT_COUNT` is the emitted static-row count and is the threshold denominator.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

`dispatch-panel.sh` emits one operator-visible launch line immediately before the waterfall dispatch, after static and dynamic slots are finalized: `→ review: launching N reviewers (X Cursor static, Y Codex static, Z dynamic)`. It is written via `larch_err`, so it appears on stderr regardless of `LARCH_QUIET_BREADCRUMBS`; when quiet mode is active the line is also mirrored into the quiet log for failure-tail visibility. The `total > 0` gate suppresses the line when no reviewers are launched.

Harness: `skills/review/scripts/test-dispatch-panel.sh`, wired through `make test-dispatch-panel`.

## Conditional reviewer pruning

`--prune-ledger FILE` enables the shared `scripts/reviewer-prune.sh filter` hook after static and dynamic rows are finalized and before the waterfall launches. When rows are removed, the unfiltered manifest is copied to `panel-manifest.pre-prune.ndjson` and the canonical `panel-manifest.ndjson` is atomically replaced with the filtered rows; `PANEL_MANIFEST` still points at the canonical basename. A filtered-empty panel emits `PANEL_PRUNED_EMPTY=true`, empty output-file KVs, `DISPATCH_OK=true`, zero slot counts, and returns before the waterfall so the caller can advance the round without treating it as degraded.
## Concise prune/log audit update

Reviewer pruning now writes a concise `prune-decision.env` for every dispatch exit. The file uses `scripts/lib-prune-decision.sh` status precedence, treats rounds outside the pruning window as `skipped`, and keeps filter warnings separate from fail-open signals.
