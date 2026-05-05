# launch-gemini-review.sh

**Purpose**: Launch Gemini as a generic-only code reviewer and normalize the Gemini CLI JSON envelope into the plain-text reviewer output consumed by `collect-agent-results.sh`.

**Invocation**: `gemini -m "$GEMINI_MODEL" -p "$PROMPT" -o json --skip-trust --approval-mode plan`, where `$GEMINI_MODEL` resolves as `${LARCH_GEMINI_MODEL:-${CLAUDE_PLUGIN_OPTION_GEMINI_MODEL:-gemini-2.5-pro}}`. The same precedence is applied by `scripts/check-reviewers.sh` for the Gemini health probe so probe and review use the same model.

## Invariants

- Generic-only v1: accepts `--output`, `--timeout`, and `--prompt`; rejects specialist flags.
- `--timeout` must be a positive integer; `0`, empty, non-digit strings, and zero-valued multi-digit strings (`00`, `000`, ...) are rejected at argv-validation time with exit 2 (parallel to `scripts/run-external-agent.sh` and the `launch-*-implement.sh` family — closes #1115, #1167). Valid leading-zero positive values like `010` are accepted and interpreted as base-10 (`010` → 10s).
- Timeout is clamped to 600 seconds before launching Gemini.
- Uses `run-external-agent.sh --capture-stdout-only` so Gemini stdout JSON is written to `<output>.raw` while stderr remains diagnostic-only.
- Requires `jq`; missing `jq` fails closed with `MISSING_JQ`, empty output, non-zero `.done`, and a diagnostic.
- Parses `.response` as the only successful output field. `.error`, missing `.response`, or empty `.response` fail closed.
- Writes normalized plain text to `--output` atomically, then writes `<output>.done` last.
- Writes `<output>.meta` with `TOOL=gemini` and `CMD_JSON=` pointing at the redacted launcher invocation, so retry paths replay JSON normalization rather than raw `gemini`. Only the on-disk encoding changed: the retry replay model remains "launcher argv with the prompt body replaced by a sha256 prefix + byte length."
- On the missing-`jq` fail-closed path, `write_meta()` deliberately omits `CMD_JSON` instead of failing before `write_done()`. The collector treats missing `CMD_JSON` as invalid retry metadata, skips retry, and marks the result/tool unhealthy.
- Rejects empty `--output` values and paths containing bytes outside `[A-Za-z0-9._/-]` before stale-file cleanup or raw wrapper launch. The same byte string is used on disk, in `OUTPUT_FILE=`, and as a standalone argv element in `CMD_JSON` that collector retry substitution rewrites, so unsafe paths fail fast instead of being transformed.
- Output filenames must carry a `gemini-` prefix when consumed by `collect-agent-results.sh` unless `.meta` is guaranteed present.

## Prompt contract

Gemini runs with `--approval-mode plan`, so callers must pass a self-contained prompt containing the diff, commit log, and changed-file list. The launcher does not call `git`.

## Test harness

`scripts/test-launch-gemini-review.sh` stubs `gemini` and exercises the real `run-external-agent.sh` path to cover timeout clamping, JSON normalization, fail-closed `.error`, `MISSING_JQ`, launcher-specific `--output` rejection before side effects, `CMD_JSON` sidecar emission, and `--timeout 0` rejection at argv-validation time.

## Edit-in-sync

Update `scripts/run-external-agent.sh`, `scripts/lib-validate-meta-path.sh`, `scripts/collect-agent-results.sh`, `scripts/check-reviewers.sh`, `skills/review/SKILL.md`, `skills/implement/SKILL.md`, `docs/external-reviewers.md`, and `SECURITY.md` when changing Gemini CLI flags, output schema, or output-path invariants. Update `.claude-plugin/plugin.json` (`gemini_model` userConfig) and `docs/configuration-and-permissions.md` (`LARCH_GEMINI_MODEL` section) when changing the model-resolution precedence or default.
