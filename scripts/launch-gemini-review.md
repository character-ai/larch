# launch-gemini-review.sh

**Purpose**: Launch Gemini as a generic-only code reviewer and normalize the Gemini CLI JSON envelope into the plain-text reviewer output consumed by `collect-agent-results.sh`.

**Invocation**: `gemini -m "$GEMINI_MODEL" -p "$PROMPT" -o json --skip-trust --approval-mode plan`, where `$GEMINI_MODEL` resolves as `${LARCH_GEMINI_MODEL:-${CLAUDE_PLUGIN_OPTION_GEMINI_MODEL:-gemini-2.5-pro}}`. The same precedence is applied by `scripts/check-reviewers.sh` for the Gemini health probe so probe and review use the same model.

## Invariants

- Generic-only v1: accepts `--output`, `--timeout`, and `--prompt`; rejects specialist flags.
- Timeout is clamped to 600 seconds before launching Gemini.
- Uses `run-external-agent.sh --capture-stdout-only` so Gemini stdout JSON is written to `<output>.raw` while stderr remains diagnostic-only.
- Requires `jq`; missing `jq` fails closed with `MISSING_JQ`, empty output, non-zero `.done`, and a diagnostic.
- Parses `.response` as the only successful output field. `.error`, missing `.response`, or empty `.response` fail closed.
- Writes normalized plain text to `--output` atomically, then writes `<output>.done` last.
- Writes `<output>.meta` with `TOOL=gemini` and `CMD=` pointing at the launcher invocation, so retry paths replay JSON normalization rather than raw `gemini`.
- Output filenames must carry a `gemini-` prefix when consumed by `collect-agent-results.sh` unless `.meta` is guaranteed present.

## Prompt contract

Gemini runs with `--approval-mode plan`, so callers must pass a self-contained prompt containing the diff, commit log, and changed-file list. The launcher does not call `git`.

## Test harness

`scripts/test-launch-gemini-review.sh` stubs `gemini` and exercises the real `run-external-agent.sh` path to cover timeout clamping, JSON normalization, fail-closed `.error`, and `MISSING_JQ`.

## Edit-in-sync

Update `scripts/run-external-agent.sh`, `scripts/collect-agent-results.sh`, `scripts/check-reviewers.sh`, `skills/review/SKILL.md`, `skills/implement/SKILL.md`, `docs/external-reviewers.md`, and `SECURITY.md` when changing Gemini CLI flags or output schema.
