# test-hook-progress-report.sh

Offline regression harness for `scripts/hook-progress-report.sh`.

It stubs the Python report engine with `HOOK_PROGRESS_TEST_MODE=1`, feeds fixture UserPromptSubmit JSON through stdin, and verifies:

- `p` and `progress` emit block JSON with the expected reason.
- Non-matching prompts (`foo`, `pp`, `P`, and empty input) are silent.
- Empty reports, bad JSON, missing `jq`, and simulated engine failures fail open.
- Multiline reports are encoded safely through `jq --arg`.
- `hooks/hooks.json` registers the hook under `UserPromptSubmit` with the shipped command path and timeout.

Makefile target: `test-hook-progress-report`.
