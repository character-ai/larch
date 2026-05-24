# test-dispatch-plan-voters.sh Contract

Regression harness for `scripts/dispatch-plan-voters.sh`.

It stubs `run-external-agent.sh`, `wait-for-reviewers.sh`, `agent-model-args.sh`, `cursor-auth-flags.sh`, `cursor-wrap-prompt.sh`, and `append-tool-failure.sh` under a temporary `CLAUDE_PLUGIN_ROOT`. Coverage includes both-tools happy path, Codex unavailable fallback, Cursor unavailable fallback, launch-failure logging, read-only/plan-mode argv shape, prompt wrapping, and a static guard that rejects direct `codex exec` / `cursor agent` command lines outside the wrapper argv construction. The wait stub polls for up to one second so asynchronous launch subshells can publish `.done` sentinels without host-timing flakes.

The harness unsets inherited session tempdir variables and points
`LARCH_EXECUTION_ISSUES_LOG` at its tempdir so logged launch failures stay
inside the harness sandbox.

Run with `bash scripts/test-dispatch-plan-voters.sh` or `make test-dispatch-plan-voters`.

Also asserts `VOTER_PATHS_FILE` KV and `plan-voter-paths.txt` contents on absent-tools and healthy stub paths.

When `CLAUDE_PLUGIN_ROOT` points at the harness stub root, the harness copies `skills/shared/scripts/render-voter-prompt.sh` into that stub so `dispatch-plan-voters.sh` can execute the shared renderer. The healthy-path assertions grep the composed prompts for the canonical finding-oos OOS clause, the informational-fix guardrail, and both `FINDING_N` / `OOS_N` example lines.
