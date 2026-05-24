# skills/implement/scripts/test-implement-bootstrap.sh — contract

`skills/implement/scripts/test-implement-bootstrap.sh` is the offline regression harness for `scripts/implement-bootstrap.sh`. The behavioral contract lives in `scripts/implement-bootstrap.md`; this sibling documents the harness only.

## Layout

- Builds a `/tmp` sandbox, copies `implement-bootstrap.sh` plus `lib-quiet.sh`, `lib-execution-issues.sh`, and the real `write-session-env.sh` / `read-session-env-key.sh` beside PATH-resolved `${SCRIPT_DIR}` peers.
- Replaces `create-branch.sh`, `session-entry-gate.sh`, `session-setup.sh`, `write-session-id.sh`, `token-claude-source.sh`, `append-tool-failure.sh`, `token-ledger.sh`, and `timing-ledger.sh` with stubs that emit canned KV / exit codes.

## Cases

| Case | Asserts |
|------|---------|
| GP1-infra | rc 0, infra keys in stdout, empty bail reason tail, no `STEP_FAILED=`. |
| GP4 | rc 0, `REPO_UNAVAILABLE=true`, repo-unavailable warning on stderr. |
| B-preflight | rc 2, `PREFLIGHT_ERROR=`, `STEP_FAILED=session-setup`, no `write-session-id` stub log. |
| B-gate | rc 2, `GATE_ERROR=` on stdout, `STEP_FAILED=session-entry-gate`, no `write-session-id` stub log. |
| Edge-NEVER14 | Static grep on live `scripts/implement-bootstrap.sh` forbids append / `cat` heredoc writes to `session-env.sh`. |
| Edge-breadcrumb-count | `LARCH_QUIET_BREADCRUMBS=1` + `LARCH_QUIET_BREADCRUMB_FD=9` → exactly one `→ step0: infra ready` line on FD 9. |
