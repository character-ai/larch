# scripts/agent-model-args.sh — contract

`scripts/agent-model-args.sh` outputs model (and optionally effort) CLI arguments for external agent tools (Codex, Cursor, Gemini). Stdout is machine-only: one argv token per physical line, with diagnostics and warnings on stderr. Codex and Cursor launch sites call it for reviews, sketches, voting, dialectic, and implementation, then read stdout into Bash arrays via `while IFS= read -r arg; do MODEL_ARGS+=("$arg"); done`. Gemini's launchers (`scripts/launch-gemini-review.sh`, `scripts/launch-gemini-implement.sh`) and health probe (`scripts/check-reviewers.sh`) do NOT call this helper; they resolve the model inline using the same precedence chain so `--model "$GEMINI_MODEL"` (or `-m "$GEMINI_MODEL"`) stays a single quoted argv token. The Gemini arm of this script defines the canonical precedence chain those inline resolvers must mirror.

This is a breaking stdout-shape change for any out-of-tree caller that expected a single shell string such as `-m gpt-5.5 -c ...`. Callers must treat each stdout line as one already-tokenized argv element and expand the resulting array with the Bash-3.2-safe `${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}` form.

## Fallback chain (Codex)

`LARCH_CODEX_MODEL` → `CLAUDE_PLUGIN_OPTION_CODEX_MODEL` → `--default-model` flag → `gpt-5.5` (hardcoded). The hardcoded default ensures all Codex invocations use gpt-5.5 unless overridden; Codex CLI's own default (5.4) is never reached.

## Fallback chain (Cursor)

`LARCH_CURSOR_MODEL` → `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL` → `composer-2` (hardcoded). The `--default-model` flag is accepted but ignored for Cursor (Cursor always has a model).

## Fallback chain (Gemini)

`LARCH_GEMINI_MODEL` → `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` → `--default-model` flag → `gemini-2.5-pro` (hardcoded). Aligned with the reviewer-side default in `scripts/launch-gemini-review.sh` and `scripts/check-reviewers.sh`. None of `scripts/launch-gemini-implement.sh`, `scripts/launch-gemini-review.sh`, or `scripts/check-reviewers.sh` (Gemini health probe) call this helper — they each resolve the model inline using the same precedence chain (without `--default-model`, which those call sites never used) to keep the `--model "$GEMINI_MODEL"` (or `-m "$GEMINI_MODEL"`) argv a single quoted token. All four precedence definitions (this helper's gemini arm + the three inline sites) must stay in lockstep when env names, plugin fallbacks, or the hardcoded default change. Gemini has no separate reasoning-effort knob in the CLI; reasoning depth is selected via the model value itself (for example, `gemini-2.5-pro` versus `gemini-2.5-flash`). `--with-effort` is accepted and intentionally emits no extra Gemini flags.

## Tool registry

The script sources `scripts/external-tool-registry.sh` for `--tool` membership validation, using a fail-closed source guard and sentinel check before argument handling. The registry owns names only; per-tool model and effort semantics stay local in this script.

The stderr wording for invalid tools remains `--tool must be 'cursor', 'codex', or 'gemini' (got: ...)` and lives as a single literal in the pre-emptive `if ! larch_is_external_tool` guard. The `case "$TOOL"` block ALSO retains a defensive `*)` arm that emits `agent-model-args.sh: internal error: unsupported reviewer tool: <id>` and exits 1; this catches drift where a future tool is added to `LARCH_EXTERNAL_TOOLS` (so `larch_is_external_tool` accepts it) but the matching per-tool model arm here is forgotten — without the defensive arm the script would silently exit 0 with empty stdout and any caller that expands this helper's stdout into a command line (e.g. the Cursor/Codex review/sketch/probe paths in `check-reviewers.sh` and elsewhere) would launch with no `--model`. The Gemini health probe in `check-reviewers.sh` resolves its model inline rather than via this helper, so it is not affected by an empty-stdout drift here. Symmetric to the `*)` arms in `scripts/check-reviewers.sh` switch helpers.

## Flags

| Flag | Purpose |
|------|---------|
| `--tool cursor\|codex\|gemini` | Required. Selects tool-specific fallback chain. |
| `--with-effort` | Opt-in. Emits Codex reasoning-effort flag (`-c model_reasoning_effort="EFFORT"`). No-op for Cursor and Gemini. |
| `--default-model MODEL` | Optional. Inserted into the Codex and Gemini fallback chains between plugin option and hardcoded default. |

## Rejection Rules

Explicit model env / plugin-option values are operator input crossing into privileged CLI argv. The producer rejects blank or whitespace-only values and any value containing a POSIX `[[:cntrl:]]` character (NUL is not representable in Bash variables, but the class includes TAB, LF, CR, ESC, and similar control bytes). Rejection exits non-zero and emits the diagnostic to stderr. Successful stdout contains no empty physical lines.

Effort warnings, including invalid `LARCH_CODEX_EFFORT`, are stderr-only. A successful stdout stream must contain only argv tokens.

## Edit-in-sync

- `scripts/agent-model-args.sh` — the script itself
- `scripts/test-agent-model-args.sh` — line-token contract and migration guard
- `scripts/test-collect-agent-bash32.sh` — regression harness (if model args affect collector behavior)
- `docs/configuration-and-permissions.md` — documents `LARCH_CODEX_MODEL`, `LARCH_CODEX_EFFORT`, `LARCH_GEMINI_MODEL` env vars
- `.claude-plugin/plugin.json` — `codex_model`, `codex_effort`, `gemini_model` userConfig entries
- `scripts/external-tool-registry.md` — update its "Sourced by" list when this script's source-list status changes
