# test-dispatch-code-voters.sh

Smoke harness for `scripts/dispatch-code-voters.sh`. Stubs every external binary (`launch-claude-subprocess.sh`, `run-external-agent.sh`, `wait-for-reviewers.sh`, `agent-model-args.sh`, `cursor-auth-flags.sh`, `cursor-wrap-prompt.sh`, `append-tool-failure.sh`) so the test runs offline and tests dispatch wiring rather than vendor responses.

## Coverage

- Argument validation: no-args → non-zero exit.
- All three voters available → 3 launches; `VOTER_N_TOOL` and `VOTER_N_STATUS=launched` correctly emitted; vote-output files present.
- Codex unavailable → Voter 2 falls back to Claude replacement (`VOTER_2_TOOL=claude`, `VOTER_2_STATUS=fallback`).
- Cursor unavailable → Voter 3 falls back to Claude replacement.
- Both externals unavailable → Voters 2 and 3 both filled by Claude replacements.

## Invocation

```bash
scripts/test-dispatch-code-voters.sh
```

Exit 0 → pass, exit 1 → at least one assertion failed.

## Stubbing pattern

Mirrors `scripts/test-dispatch-plan-voters.sh`: a fresh PLUGIN_ROOT directory is populated with stub scripts that write deterministic outputs/sentinels. The script under test is copied into the stub root so its `CLAUDE_PLUGIN_ROOT` resolution finds the stubs.
