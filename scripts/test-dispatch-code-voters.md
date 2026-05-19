# test-dispatch-code-voters.sh

Smoke harness for `scripts/dispatch-code-voters.sh`. Stubs every external binary (`launch-claude-subprocess.sh`, `run-external-agent.sh`, `wait-for-reviewers.sh`, `agent-model-args.sh`, `cursor-auth-flags.sh`, `cursor-wrap-prompt.sh`, `append-tool-failure.sh`) so the test runs offline and tests dispatch wiring rather than vendor responses.

## Coverage

11 scenarios split across 6 `--section` groups for CI shard packing:

- `happy` (scenarios 1-3): all voters available; codex/cursor absent; voter1 fails.
- `edge` (scenarios 4-5): symlink diff; 2 MB diff.
- `retry-claude` (scenarios 6-7): claude voter parse-rate retry success; parse-rate retry failure.
- `retry-codex-success` (scenario 8): codex voter parse-rate retry success.
- `retry-cursor` (scenario 9): cursor voter parse-rate retry success.
- `retry-codex-fail-and-fallback` (scenarios 10-11): codex parse-rate retry failure; all-claude fallback parse-rate failure.

## Invocation

```bash
scripts/test-dispatch-code-voters.sh
```

Run a single section:

```bash
scripts/test-dispatch-code-voters.sh --section happy
```

Exit 0 → pass, exit 1 → at least one assertion failed.

## Stubbing pattern

Mirrors `scripts/test-dispatch-plan-voters.sh`: a fresh PLUGIN_ROOT directory is populated with stub scripts that write deterministic outputs/sentinels. The script under test is copied into the stub root so its `CLAUDE_PLUGIN_ROOT` resolution finds the stubs.
