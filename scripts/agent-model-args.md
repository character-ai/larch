# scripts/agent-model-args.sh — contract

`scripts/agent-model-args.sh` outputs model (and optionally effort) CLI arguments for external agent tools (Codex, Cursor, Gemini). External-agent launch sites call it when they support configurable model flags — reviews, sketches, voting, dialectic, and implementation for Codex/Cursor, and implementation for Gemini.

## Fallback chain (Codex)

`LARCH_CODEX_MODEL` → `CLAUDE_PLUGIN_OPTION_CODEX_MODEL` → `--default-model` flag → `gpt-5.5` (hardcoded). The hardcoded default ensures all Codex invocations use gpt-5.5 unless overridden; Codex CLI's own default (5.4) is never reached.

## Fallback chain (Cursor)

`LARCH_CURSOR_MODEL` → `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL` → `composer-2` (hardcoded). The `--default-model` flag is accepted but ignored for Cursor (Cursor always has a model).

## Fallback chain (Gemini)

`LARCH_GEMINI_MODEL` → `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` → `--default-model` flag → `gemini-2.5-pro` (hardcoded). Used by the Gemini implementer launcher and aligned with the reviewer-side default in `scripts/launch-gemini-review.sh` and `scripts/check-reviewers.sh`. Gemini has no separate reasoning-effort knob in the CLI; reasoning depth is selected via the model value itself (for example, `gemini-2.5-pro` versus `gemini-2.5-flash`). `--with-effort` is accepted and intentionally emits no extra Gemini flags.

## Tool registry

The script sources `scripts/external-tool-registry.sh` for `--tool` membership validation, using a fail-closed source guard and sentinel check before argument handling. The registry owns names only; per-tool model and effort semantics stay local in this script.

The stderr wording for invalid tools remains `--tool must be 'cursor', 'codex', or 'gemini' (got: ...)` and lives as a single literal in the pre-emptive `if ! larch_is_external_tool` guard. The `case "$TOOL"` block ALSO retains a defensive `*)` arm that emits `agent-model-args.sh: internal error: unsupported reviewer tool: <id>` and exits 1; this catches drift where a future tool is added to `LARCH_EXTERNAL_TOOLS` (so `larch_is_external_tool` accepts it) but the matching per-tool model arm here is forgotten — without the defensive arm the script would silently exit 0 with empty stdout and callers like `check-reviewers.sh` would launch probes with no `--model`. Symmetric to the `*)` arms in `scripts/check-reviewers.sh` switch helpers.

## Flags

| Flag | Purpose |
|------|---------|
| `--tool cursor\|codex\|gemini` | Required. Selects tool-specific fallback chain. |
| `--with-effort` | Opt-in. Emits Codex reasoning-effort flag (`-c model_reasoning_effort="EFFORT"`). No-op for Cursor and Gemini. |
| `--default-model MODEL` | Optional. Inserted into the Codex and Gemini fallback chains between plugin option and hardcoded default. |

## Edit-in-sync

- `scripts/agent-model-args.sh` — the script itself
- `scripts/test-collect-agent-bash32.sh` — regression harness (if model args affect collector behavior)
- `docs/configuration-and-permissions.md` — documents `LARCH_CODEX_MODEL`, `LARCH_CODEX_EFFORT`, `LARCH_GEMINI_MODEL` env vars
- `.claude-plugin/plugin.json` — `codex_model`, `codex_effort`, `gemini_model` userConfig entries
- `scripts/external-tool-registry.md` — update its "Sourced by" list when this script's source-list status changes
