# dispatch-plan-voters.sh Contract

`scripts/dispatch-plan-voters.sh` launches the external `/design` Step 3 plan-review voters: Voter 2 (Codex) and Voter 3 (Cursor).

The script is the single plan-review voter path for external tools. It fails closed when `scripts/run-external-agent.sh` is missing, so plan-review voting cannot bypass the monitored wrapper. Available tools are launched through `run-external-agent.sh`; unavailable tools emit `VOTER_N_STATUS=fallback` so the `/design` orchestrator launches the Claude replacement voter through the Agent tool.

Inputs are `--ballot-file`, `--design-tmpdir`, `--codex-available`, `--cursor-available`, and optional `--session-env-path`. The ballot is referenced by path in the voter prompt rather than inlined.

Codex runs as `codex exec --sandbox read-only -C "$PWD"` with model and effort argv from `scripts/agent-model-args.sh --tool codex --with-effort`. Cursor runs as `cursor agent -p --trust --mode plan --workspace "$PWD"` with model argv from `agent-model-args.sh`, auth argv from `scripts/cursor-auth-flags.sh`, and prompt wrapping through `scripts/cursor-wrap-prompt.sh`.

The script waits for launched external voters via `scripts/wait-for-reviewers.sh --timeout 1260`. Launch and wait failures append captured logs to `execution-issues.md` through `scripts/append-tool-failure.sh` under `External Reviewer Issues` when that helper is available. The log path resolver uses `LARCH_EXECUTION_ISSUES_LOG` when set; otherwise it falls back through `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`, `$IMPLEMENT_TMPDIR/execution-issues.md`, then `$DESIGN_TMPDIR/execution-issues.md`.

Stdout is `KEY=value` only: `VOTER_2_PATH`, `VOTER_3_PATH`, `VOTER_2_STATUS`, `VOTER_3_STATUS`, and `DISPATCH_OK`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `scripts/test-dispatch-plan-voters.sh`, wired through `make test-dispatch-plan-voters`.
