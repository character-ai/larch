# test-dispatch-plan-voters.sh Contract

Regression harness for `scripts/dispatch-plan-voters.sh`.

It stubs `run-external-agent.sh`, `wait-for-reviewers.sh`, `agent-model-args.sh`, `cursor-auth-flags.sh`, `cursor-wrap-prompt.sh`, and `append-tool-failure.sh` under a temporary `CLAUDE_PLUGIN_ROOT`. Coverage includes both-tools happy path, Codex unavailable fallback, Cursor unavailable fallback, launch-failure logging, read-only/plan-mode argv shape, prompt wrapping, and a static guard that rejects direct `codex exec` / `cursor agent` command lines outside the wrapper argv construction.

Run with `bash scripts/test-dispatch-plan-voters.sh` or `make test-dispatch-plan-voters`.
