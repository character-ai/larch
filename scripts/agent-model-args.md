# scripts/agent-model-args.sh — contract

`scripts/agent-model-args.sh` outputs model (and optionally effort) CLI arguments for external agent tools (Codex, Cursor, Gemini). Called by every external-agent launch site — reviews, sketches, voting, dialectic, and implementer launchers.

## Fallback chain (Codex)

`LARCH_CODEX_MODEL` → `CLAUDE_PLUGIN_OPTION_CODEX_MODEL` → `--default-model` flag → `gpt-5.5` (hardcoded). The hardcoded default ensures all Codex invocations use gpt-5.5 unless overridden; Codex CLI's own default (5.4) is never reached.

## Fallback chain (Cursor)

`LARCH_CURSOR_MODEL` → `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL` → `composer-2` (hardcoded). The `--default-model` flag is accepted but ignored for Cursor (Cursor always has a model).

## Fallback chain (Gemini)

`LARCH_GEMINI_MODEL` → `--default-model` flag → `gemini-2.5-pro` (hardcoded). `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` is bridged to `LARCH_GEMINI_MODEL` in `scripts/session-setup.sh`; this helper consumes only `LARCH_GEMINI_MODEL`.

## Flags

| Flag | Purpose |
|------|---------|
| `--tool cursor\|codex\|gemini` | Required. Selects tool-specific fallback chain. |
| `--with-effort` | Opt-in. Emits Codex reasoning-effort flag (`-c model_reasoning_effort="EFFORT"`). No-op for Cursor and Gemini. Gemini implementer max reasoning is requested by prompt prefix in `launch-gemini-implement.sh`. |
| `--default-model MODEL` | Optional. Inserted into the Codex and Gemini fallback chains before the hardcoded default. |

## Edit-in-sync

- `scripts/agent-model-args.sh` — the script itself
- `scripts/test-collect-agent-bash32.sh` — regression harness (if model args affect collector behavior)
- `docs/configuration-and-permissions.md` — documents `LARCH_CODEX_MODEL`, `LARCH_CODEX_EFFORT` env vars
- `.claude-plugin/plugin.json` — `codex_model`, `codex_effort` userConfig entries
- `scripts/session-setup.sh` — bridges `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` to `LARCH_GEMINI_MODEL`
