# test-dispatch-code-voters.sh

Smoke harness for `scripts/dispatch-code-voters.sh`. Stubs every external binary (`launch-claude-subprocess.sh`, `run-external-agent.sh`, `wait-for-reviewers.sh`, `agent-model-args.sh`, `cursor-auth-flags.sh`, `cursor-wrap-prompt.sh`, `append-tool-failure.sh`) so the test runs offline and tests dispatch wiring rather than vendor responses.

The harness unsets `LARCH_EXECUTION_ISSUES_LOG`, `SESSION_ENV_PATH`, and `IMPLEMENT_TMPDIR` at startup so parent `/implement` env vars never leak into test invocations. Tests that assert on issues-log writes set `LARCH_EXECUTION_ISSUES_LOG` explicitly on each individual invocation.

## Coverage

11 scenarios split across 6 `--section` groups for CI shard packing:

- `happy` (scenarios 1-3): all voters available; codex/cursor absent; voter1 fails.
- `edge` (scenarios 4-5): symlink diff; 2 MB diff.
- `retry-claude` (scenarios 6-7): claude voter parse-rate retry success; parse-rate retry failure.
- `retry-codex-success` (scenario 8): codex voter parse-rate retry success.
- `retry-cursor` (scenario 9): cursor voter parse-rate retry success.
- `retry-codex-fail-and-fallback` (scenarios 10-11): codex parse-rate retry failure; all-claude fallback parse-rate failure.
- Regression: env isolation — `LARCH_EXECUTION_ISSUES_LOG` passed explicitly but `REVIEW_TMPDIR` is nested under a harness tmpdir; parent issues-log not written.
- Regression: harness-ancestor path guard — local diag file written; issues-log suppressed when `REVIEW_TMPDIR` and `voter_path` stay inside the same harness tree.
- Regression: production-shape — `REVIEW_TMPDIR` outside the harness prefixes; both local diag file and issues-log written.

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
