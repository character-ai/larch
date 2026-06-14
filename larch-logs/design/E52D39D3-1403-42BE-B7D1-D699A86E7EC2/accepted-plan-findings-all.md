### FINDING_1: Plugin-cache CWD defeats naive consumer-repo workdir resolution
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned fix (`_resolve_consumer_repo_root(str(Path.cwd()))` at `python/agents.py:3540`) is insufficient when `run_legacy_script` forces CWD to the managed plugin-cache directory. That path is typically not a git repository root, so `git -C <cwd> rev-parse --show-toplevel` fails and the helper falls back to the same cache cwd. Codex is then launched with `-C` on the plugin cache (confirmed by `OUTER_LAUNCHER_WORKDIR` in slot metadata), fails the trusted-directory git check, and never reviews the consumer repo. Walking up from `Path.cwd()` alone does not reliably reach the operator's consumer repo in this invocation chain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Resolve workdir like scripts/run-relevant-checks-captured.sh: prefer CLAUDE_PROJECT_DIR (git -C validated to toplevel), then git -C cwd rev-parse --show-toplevel, then fallback to cwd
  - From Cursor-Pragmatic: OUTER_LAUNCHER_WORKDIR meta confirms this path. session_env.py already writes CLONE_PATH=<consumer repo> into DESIGN_TMPDIR/.larch-keepalive at session setup (progress_report.py reads it). Extend _review_launch_codex workdir resolution: after git rev-parse on cwd, if still not a git root walk output parents for .larch-keepalive, read CLONE_PATH, and resolve workdir from that path before final cwd fallback




### FINDING_2: Keepalive workdir test must unset CLAUDE_PROJECT_DIR
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The keepalive workdir test must unset `CLAUDE_PROJECT_DIR` before launch. If the pytest process inherits `CLAUDE_PROJECT_DIR`, tier 1 resolves the consumer repo and the keepalive test passes without exercising tier 3, so a broken `CLONE_PATH` recovery could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add `monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)` to `codex_launch_resolves_workdir_from_plugin_cache_via_keepalive` before calling `_review_launch_codex`.




### FINDING_2: Unclassified retry ordering underspecified in `_run_external_agent_with_auth_retries`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The unclassified retry in `_run_external_agent_with_auth_retries` is underspecified relative to the attempt-limit early return. The plan adds a one-shot unclassified exit-1 retry inside the existing `for attempt in range(1, _auth_retry_limit()+1)` loop but does not require that retry to run before `if result.exit_code == 0 or attempt >= _auth_retry_limit(): return result`. A literal implementation can skip the blind retry on the final loop iteration (including when `LARCH_EXTERNAL_AUTH_RETRIES=1`), defeating the issue's secondary prescription.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify ordering explicitly: evaluate `_is_unclassified_empty_startup_failure` immediately after `run_external_agent` and before the attempt-limit return; allow exactly one extra iteration (or a pre-return `continue`) that is not gated by `attempt >= _auth_retry_limit()`.


### FINDING_3: Missing one-shot guard in `_review_run_with_retries`
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: `_review_run_with_retries` omits an explicit one-shot guard for the unclassified empty exit-1 retry. The plan adds `unclassified_empty_retried` for `_run_external_agent_with_auth_retries` but only says increment `auth_attempt` for `_review_run_with_retries`. The `while auth_attempt <= max_auth` loop can repeat the unclassified branch on every iteration until the auth budget is exhausted, violating the stated one-time blind retry and failure-mode cap of one extra attempt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Mirror the `_run_external_agent_with_auth_retries` contract: track `unclassified_empty_retried` (or equivalent) in `_review_run_with_retries` and gate the `continue` path on it; keep `auth_attempt` increment for telemetry only.



### FINDING_1: Unclassified retry cannot run when auth budget is 1
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The plan specifies the unclassified one-shot retry as `continue` inside the existing auth-bounded loops (`for attempt in range(1, _auth_retry_limit() + 1)` in `_run_external_agent_with_auth_retries` and `while auth_attempt <= max_auth` in `_review_run_with_retries`). When `LARCH_EXTERNAL_AUTH_RETRIES=1`, those loops only allow one iteration: in the `for` loop, `continue` after the first empty exit-1 exits the loop with no second runner call; in the review helper, incrementing `auth_attempt` to 2 before `continue` makes `2 <= 1` false and also skips the second launch. `_run_external_agent_with_auth_retries` also returns immediately on `attempt >= _auth_retry_limit()` at line 2174. This contradicts the plan’s mandated tests (e.g. `unclassified_empty_exit_one_respects_auth_retry_limit_one`, `codex_retry_unclassified_empty_exit_one` with low limits) and Failure modes, which require two total calls (one auth-budget attempt plus one bonus unclassified retry).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify loop shape that grants exactly one bonus launch outside the auth budget (e.g. `while` with an explicit bonus slot, or `range(1, max_auth + 2)` with the unclassified branch allowed only once), and mirror the `LARCH_EXTERNAL_AUTH_RETRIES=1` test on `_review_run_with_retries`.
  - From Codex-Generic: Replace bounded-loop `continue` with a structure that allows one bonus launch outside the auth budget: e.g. inline a second `run_external_agent` / `_review_run_wrapper_attempt` call in the same iteration, or switch to a `while` loop with separate counters for auth-budget retries vs the one-shot unclassified retry. Do not increment `auth_attempt` before the while guard unless the loop condition explicitly permits the bonus attempt.



