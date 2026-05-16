# scripts/agent-model-args.sh — contract

This is a breaking stdout-shape change for any out-of-tree caller that expected a single shell string such as `-m gpt-5.5 -c ...`. Callers must treat each stdout line as one already-tokenized argv element and expand the resulting array with the Bash-3.2-safe `${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}` form.

## Fallback chain (Codex)

`LARCH_CODEX_MODEL` → `CLAUDE_PLUGIN_OPTION_CODEX_MODEL` → `--default-model` flag → `gpt-5.5` (hardcoded). The hardcoded default ensures all Codex invocations use gpt-5.5 unless overridden; Codex CLI's own default (5.4) is never reached.

## Fallback chain (Cursor)

`LARCH_CURSOR_MODEL` → `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL` → `composer-2` (hardcoded). The `--default-model` flag is accepted but ignored for Cursor (Cursor always has a model).

## Tool registry

The script sources `scripts/external-tool-registry.sh` for `--tool` membership validation, using a fail-closed source guard and sentinel check before argument handling. The registry owns names only; per-tool model and effort semantics stay local in this script.

## Flags

| Flag | Purpose |
|------|---------|

## Rejection Rules

Explicit model env / plugin-option values are operator input crossing into privileged CLI argv. The producer rejects blank or whitespace-only values and any value containing a POSIX `[[:cntrl:]]` character (NUL is not representable in Bash variables, but the class includes TAB, LF, CR, ESC, and similar control bytes). Rejection exits non-zero and emits the diagnostic to stderr. Successful stdout contains no empty physical lines.

Effort warnings, including invalid `LARCH_CODEX_EFFORT`, are stderr-only. A successful stdout stream must contain only argv tokens.

## Edit-in-sync

- `scripts/agent-model-args.sh` — the script itself
- `scripts/test-agent-model-args.sh` — line-token contract and migration guard
- `scripts/test-collect-agent-bash32.sh` — regression harness (if model args affect collector behavior)
- `scripts/external-tool-registry.md` — update its "Sourced by" list when this script's source-list status changes
