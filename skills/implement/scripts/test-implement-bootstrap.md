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
| B2-plan | CLOSED target issue on `--up-to-phase plan` preserves `IMPLEMENT_BAIL_REASON=adopted-issue-closed` and does not overwrite it with a phase-3 placeholder. |
| B3 | PR target emits `IMPLEMENT_BAIL_REASON=adopted-issue-is-pr`. |
| B4 | `POSTED=false` emits `DEFERRED=true`, exits 0, and removes any stale sentinel. |
| B5 | `larch-log.sh init` failure emits `IMPLEMENT_BAIL_REASON=tracking-init-failed` and `STALL_TRACKING=true`. |
| B5-all | `larch-log.sh init` failure on `--up-to-phase all` preserves `IMPLEMENT_BAIL_REASON=tracking-init-failed` and skips later placeholder bail reasons. |
| B5-plan | `larch-log.sh init` failure on `--up-to-phase plan` preserves `IMPLEMENT_BAIL_REASON=tracking-init-failed` and skips the phase-3 placeholder. |
| B5-branch1 | Branch 1 sentinel resume with `larch-log.sh init` failure preserves the sentinel issue/run id while stalling tracking. |
| B6 | `get-issue-state.sh` failure exits 2 with `STEP_FAILED=get-issue-state`. |
| B7-non-open-state | Unexpected non-`OPEN`/`CLOSED` issue state exits 2 with `STEP_FAILED=get-issue-state`. |
| B-sentinel-malformed | Malformed sentinel is cleared and replaced via Branch 2 fresh adoption. |
| B-sentinel-invalid-run-id | Sentinel with invalid `RUN_ID` is cleared and replaced via Branch 2 fresh adoption. |
| B-empty-run-id-derivation | Empty derived run id stalls tracking with `IMPLEMENT_BAIL_REASON=tracking-init-failed`. |
| GP-adopt-rename-fail | Branch 2 adoption continues after rename failure and appends an execution-issues entry. |
| GP2-rename-fail | Branch 1 resume continues after rename failure and appends an execution-issues entry. |
| B-preflight | rc 2, `PREFLIGHT_ERROR=`, `STEP_FAILED=session-setup`, no `write-session-id` stub log. |
| B-gate | rc 2, `GATE_ERROR=` on stdout, `STEP_FAILED=session-entry-gate`, no `write-session-id` stub log. |
| B-issue-required-for-resume | Existing sentinel without argv `--issue-number` exits 2 with `STEP_FAILED=issue-number-required-for-resume`. |
| B-fork-missing-issue | `--forked-target true --upstream-repo OWNER/REPO` without `--issue-number` exits 2 with a usage error. |
| B-invalid-run-id-arg | Invalid `--run-id` exits 2 with a usage error. |
| B-invalid-upstream-repo-arg | Invalid `--upstream-repo` exits 2 with a usage error. |
| Edge-NEVER14 | Static grep on live `scripts/implement-bootstrap.sh` forbids append / `cat` heredoc writes to `session-env.sh`. |
| Edge-breadcrumb-count | `LARCH_QUIET_BREADCRUMBS=1` + `LARCH_QUIET_BREADCRUMB_FD=1` → exactly one `→ step0: infra ready` line. |
| Edge-breadcrumb-count-adopt | `LARCH_QUIET_BREADCRUMBS=1` + tracking adoption → exactly one `→ step0: tracking adopted` line. |
