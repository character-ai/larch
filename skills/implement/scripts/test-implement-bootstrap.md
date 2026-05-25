# skills/implement/scripts/test-implement-bootstrap.sh — contract

`skills/implement/scripts/test-implement-bootstrap.sh` is the offline regression harness for `scripts/implement-bootstrap.sh`. The behavioral contract lives in `scripts/implement-bootstrap.md`; this sibling documents the harness only.

## Layout

- Builds a `/tmp` sandbox, copies `implement-bootstrap.sh` plus `lib-quiet.sh`, `lib-execution-issues.sh`, and the real `write-session-env.sh` / `read-session-env-key.sh` beside PATH-resolved `${SCRIPT_DIR}` peers.
- Replaces `create-branch.sh`, `session-entry-gate.sh`, `session-setup.sh`, `write-session-id.sh`, `token-claude-source.sh`, `append-tool-failure.sh`, `token-ledger.sh`, `timing-ledger.sh`, `tracking-issue-read.sh`, `get-issue-state.sh`, `larch-log.sh`, `post-tracking-issue.sh`, `tracking-issue-write.sh`, and `get-issue-context.sh` with stubs that emit canned KV / exit codes.

## Cases

| Case | Asserts |
|------|---------|
| GP1-infra | rc 0, infra keys in stdout, empty bail reason tail, no `STEP_FAILED=`. |
| GP-adopt | Branch 2 fresh adoption emits issue/run ids, `BRANCH_SELECTED=branch-2-adopt`, `DEFERRED=false`, `STALL_TRACKING=false`, and writes the sentinel with the selected `RUN_ID`. |
| GP2 | Branch 1 sentinel resume emits `BRANCH_SELECTED=branch-1-resume` and reuses sentinel `ISSUE_NUMBER` / `RUN_ID`. |
| GP3 | Fork mode emits `BRANCH_SELECTED=forked-target-skip`, empty `ISSUE_NUMBER`, `DEFERRED=true`, and writes `FORKED_TARGET=true` to session-env. |
| GP-repo-unavail-tracking | Tracking phase with `REPO_UNAVAILABLE=true` emits `BRANCH_SELECTED=repo-unavailable-skip`, empty `ISSUE_NUMBER`, and `DEFERRED=true`. |
| GP4 | Infra-only repo-unavailable path emits `REPO_UNAVAILABLE=true` and repo-unavailable warning on stderr. |
| B1 | Sentinel issue mismatch clears and replaces the sentinel via Branch 2 fresh adoption. |
| B2 | CLOSED target issue emits `IMPLEMENT_BAIL_REASON=adopted-issue-closed`. |
| B3 | PR target emits `IMPLEMENT_BAIL_REASON=adopted-issue-is-pr`. |
| B4 | `POSTED=false` emits `DEFERRED=true`, exits 0, and leaves no sentinel. |
| B5 | `larch-log.sh init` failure emits `IMPLEMENT_BAIL_REASON=tracking-init-failed` and `STALL_TRACKING=true`. |
| B6 | `get-issue-state.sh` failure exits 2 with `STEP_FAILED=get-issue-state`. |
| B-sentinel-malformed | Malformed sentinel is cleared and replaced via Branch 2 fresh adoption. |
| B-preflight | rc 2, `PREFLIGHT_ERROR=`, `STEP_FAILED=session-setup`, no `write-session-id` stub log. |
| B-gate | rc 2, `GATE_ERROR=` on stdout, `STEP_FAILED=session-entry-gate`, no `write-session-id` stub log. |
| Edge-NEVER14 | Static grep on live `scripts/implement-bootstrap.sh` forbids append / `cat` heredoc writes to `session-env.sh`. |
| Edge-breadcrumb-count | `LARCH_QUIET_BREADCRUMBS=1` + `LARCH_QUIET_BREADCRUMB_FD=1` → exactly one `→ step0: infra ready` line. |
