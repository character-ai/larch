### [Plan Review] FINDING_3

### FINDING_3: Inner sentinel promotion lacks EXIT trap safety net
- **Reviewer(s)**: Cursor-dyn-sidecar-contract
- **Severity**: latent
- **Concern**: The plan promotes the inner sentinel only via an explicit post-loop `codex_launcher_promote_inner_done` call and does not install an EXIT trap like `launch-review` `_codex_exit_dispatcher`. If post-processing after the final `run-external-agent` attempt aborts (`set -e`, signal, OOM) before the explicit promote runs, only `${OUTPUT}.inner.done` exists and `collect-agent-results.sh` / `wait-for-reviewers.sh` poll `${OUTPUT}.done` until timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sidecar-contract: Mirror launch-review.sh:262-282: install an EXIT trap that always calls `codex_launcher_promote_inner_done` before exit, with the explicit post-loop promote kept as the normal-path fast path


### [Plan Review] FINDING_4

### FINDING_4: lint-codex-exec-auth rule misses same-line embedded `codex exec`
- **Reviewer(s)**: Cursor-dyn-lint-scope
- **Severity**: latent
- **Concern**: The proposed shell rule matches only when `codex exec` is the line command word after leading `VAR=value` stripping; same-line argv embedding after `run-external-agent.sh --` is invisible. A contributor can copy the established one-line launcher shape (e.g. `CODEX_HOME=… run-external-agent.sh … -- codex exec …` as in `launch-codex-implement` runtime logs) into a non-allowlisted `scripts/*.sh` file and make `lint-codex-exec-auth` pass while leaving `OPENAI_API_KEY` unwired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-lint-scope: Also flag lines where a stripped prefix is followed by a command and the line contains a `-- codex exec` token (or extend the harness with a same-line fixture); keep negotiation on its own `codex exec` command-word line with pragma


