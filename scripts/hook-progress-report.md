# hook-progress-report.sh

UserPromptSubmit hook registered in `hooks/hooks.json` for zero-turn larch progress reports. When the submitted prompt, after trimming whitespace, exactly matches lowercase `p` or `progress`, the hook asks the Python runtime for a progress report and blocks the prompt with that report as the hook reason. All other prompts pass through silently.

## Purpose

Provides on-demand visibility into long-running `/implement` and `/design` runs without invoking the model or adding report text to conversation context. The common no-match path parses the hook JSON and exits immediately.

## Inputs

Reads Claude Code hook JSON from stdin:

- `prompt` — trimmed and matched exactly against `p` or `progress`.
- `cwd` — forwarded to `python/cli.py progress report --cwd` so the engine selects a live run for the same repository.

## Output

On a matching prompt with a non-empty report, emits `{"decision":"block","reason":"..."}`. The JSON is built with `jq --arg` so multiline report text is encoded safely. Empty reports, parse errors, missing `jq`, engine failures, or any other unexpected condition exit 0 with no output.

## Fail-open invariant

Never blocks ordinary prompts on internal failure; `set -e` is intentionally omitted. The hook performs no network calls and writes no files.

## Test harness

`scripts/test-hook-progress-report.sh` covers match/no-match behavior, no-live-run and error fail-open paths, multiline reason encoding, and the `hooks/hooks.json` registration.
