# skills/implement/scripts/test-implement-bootstrap.sh — contract

`skills/implement/scripts/test-implement-bootstrap.sh` is the offline regression harness for `scripts/implement-bootstrap.sh`. The behavioral contract lives in `scripts/implement-bootstrap.md`; this sibling documents the harness only.

## Layout

- Builds a `/tmp` sandbox, copies `implement-bootstrap.sh` plus `lib-quiet.sh`, `lib-execution-issues.sh`, and the real `write-session-env.sh` / `read-session-env-key.sh` beside PATH-resolved `${SCRIPT_DIR}` peers. `$SANDBOX/bin` is prepended to `PATH` for the `gh` stub.
- Replaces `create-branch.sh`, `session-entry-gate.sh`, `session-setup.sh`, `write-session-id.sh`, `token-claude-source.sh`, `append-tool-failure.sh`, `token-ledger.sh`, `timing-ledger.sh`, `tracking-issue-read.sh`, `get-issue-state.sh`, `larch-log.sh`, `post-tracking-issue.sh`, `tracking-issue-write.sh`, `get-issue-context.sh`, and Phase 3 helpers with stubs that emit canned KV / exit codes.

## Cases

| Case | Asserts |
|------|---------|
| GP1-infra | rc 0, infra keys in stdout, empty bail reason tail, no `STEP_FAILED=`. |
| GP-adopt | Branch 2 fresh adoption emits issue/run ids, `BRANCH_SELECTED=branch-2-adopt`, `DEFERRED=false`, `STALL_TRACKING=false`, writes the sentinel with the selected `RUN_ID`, and emits the `Step 0 — tracking issue` token/timing marks once. |
| GP2 | Branch 1 sentinel resume emits `BRANCH_SELECTED=branch-1-resume` and reuses sentinel `ISSUE_NUMBER` / `RUN_ID`. |
| GP3 | Fork mode emits `BRANCH_SELECTED=forked-target-skip`, empty `ISSUE_NUMBER`, `DEFERRED=true`, writes `FORKED_TARGET=true` to session-env, and still emits the `Step 0 — tracking issue` token/timing marks once. |
| GP3-upstream-context-fail | Fork mode still continues when `get-issue-context.sh` fails and appends a redacted Warning entry to `execution-issues.md`. |
| GP-repo-unavail-tracking | Tracking phase with `REPO_UNAVAILABLE=true` emits `BRANCH_SELECTED=repo-unavailable-skip`, empty `ISSUE_NUMBER`, `DEFERRED=true`, and still emits the `Step 0 — tracking issue` token/timing marks once. |
| GP-repo-unavail-plan | Repo-unavailable `--up-to-phase plan` still snapshots the untracked baseline, but skips `gh issue view`, run-flags persist, dirty-tree checkpoint, branch creation/capture, plan logging, and summary upsert; `PLAN_FILE` stays empty. |
| GP4 | Infra-only repo-unavailable path emits `REPO_UNAVAILABLE=true` and repo-unavailable warning on stderr. |
| B1 | Sentinel issue mismatch clears and replaces the sentinel via Branch 2 fresh adoption. |
| B2 | CLOSED target issue emits `IMPLEMENT_BAIL_REASON=adopted-issue-closed`. |
| B2-plan | CLOSED target issue on `--up-to-phase plan` preserves `IMPLEMENT_BAIL_REASON=adopted-issue-closed` and does not overwrite it with Phase 3 bail reasons. |
| B3 | PR target emits `IMPLEMENT_BAIL_REASON=adopted-issue-is-pr`. |
| B4 | Rename fires before `post-tracking-issue.sh`; `POSTED=false` then emits `DEFERRED=true`, exits 0, and removes any stale sentinel. |
| B5 | `larch-log.sh init` failure emits `IMPLEMENT_BAIL_REASON=tracking-init-failed` and `STALL_TRACKING=true`. |
| B5-all | `larch-log.sh init` failure on `--up-to-phase all` preserves `IMPLEMENT_BAIL_REASON=tracking-init-failed` and skips later placeholder bail reasons. |
| B5-plan | `larch-log.sh init` failure on `--up-to-phase plan` preserves `IMPLEMENT_BAIL_REASON=tracking-init-failed` and skips the phase-3 placeholder. |
| B5-branch1 | Branch 1 sentinel resume with `larch-log.sh init` failure preserves the sentinel issue/run id while stalling tracking. |
| B5-plan-green | Phase 3 green path copies the Preflight plan, composes issue context, persists run flags, creates/captures the derived branch, writes plan batches, upserts `larch:plan`, and covers three slug inputs. |
| B5-plan-emergency | Emergency plan materialization persists `EMERGENCY_REQUESTED=true`, refreshes tracking metadata with the same flag, and appends the bypass log once. |
| B5-plan-emergency-invalid-format | Invalid bypass logs downgrade to a redacted invalid-format Warning entry instead of failing the run. |
| B5-plan-best-effort-failures | Non-fatal `run-step1-plan-log.sh`, `write-tally.sh`, and `tracking-issue-summary.sh` failures append Warnings and still return a green Phase 3 tail. |
| B5-plan-goal-redaction-failure | Goal-text redaction fails closed to a placeholder and appends a Warning instead of logging the raw issue title. |
| B6-plan-flags | Any non-zero `persist-implement-run-flags.sh` exit emits `IMPLEMENT_BAIL_REASON=run-flags-persist-failed`, sets `STALL_TRACKING=true`, and stops subsequent Phase 3 helpers. |
| B7-plan-dirty-tree | `STATUS=dirty` and `STATUS=unknown` emit `IMPLEMENT_BAIL_REASON=dirty-tree` without setting `STALL_TRACKING`, and stop subsequent Phase 3 helpers. |
| B7-plan-dirty-tree probe-failure | Dirty-tree checkpoint probe failure is treated as `STATUS=unknown`, preserving the `dirty-tree` bail and stopping the tail. |
| B7-plan-dirty-tree resume-tail | `--resume-plan-tail` re-runs the dirty-tree checkpoint inside the same tmpdir after a prior dirty-tree bail: clean resumes the post-checkpoint tail, dirty/unknown preserves `IMPLEMENT_BAIL_REASON=dirty-tree`, both paths avoid duplicate snapshot / `gh` work, emergency resumes preserve prior `EMERGENCY_REQUESTED=true` when argv omits the flag, and bypass-log warnings are not replayed. |
| B4-plan-dirty-resume | `POSTED=false` + dirty-tree bail resumes Phase 3 tail from existing plan artifacts without requiring a tracking sentinel, and still avoids duplicate snapshot / `gh` work. |
| B8-plan-forked-target | Fork mode still materializes plan/feature files with upstream `gh --repo`, skips branch creation, captures the current branch, and skips the local `larch:plan` upsert. |
| B9-plan-user-branch | Existing user branch skips branch creation but still writes the local `larch:plan` summary. |
| B10-plan-missing-preflight-tmpdir | `--up-to-phase plan --issue-number N` without `--preflight-tmpdir` exits 2 with usage. |
| B11-plan-copy-plan-failure | Missing `plan-from-issue.txt` exits 2 with `STEP_FAILED=copy-plan`. |
| B12-plan-gh-issue-view-failure | `gh issue view` failure exits 2 with `STEP_FAILED=gh-issue-view`. |
| B13-plan-branch-create | Branch creation failure stalls tracking with `IMPLEMENT_BAIL_REASON=branch-create-failed` before branch capture or plan logs. |
| B14-plan-branch-capture | Branch capture failure or empty `BRANCH=` stalls tracking with `IMPLEMENT_BAIL_REASON=branch-create-failed` after create-branch. |
| B15-resume-plan-tail-sentinel-mismatch | `--resume-plan-tail` with a sentinel that targets a different issue exits 2 with `STEP_FAILED=resume-plan-tail-sentinel` before any Phase 3 tail helper runs. |
| B16-resume-plan-tail-sentinel-malformed | `--resume-plan-tail` with a malformed or invalid adopted sentinel exits 2 with `STEP_FAILED=resume-plan-tail-sentinel` before any Phase 3 tail helper runs. |
| B17-resume-plan-tail-sentinel-missing | `--resume-plan-tail` without a sentinel and without existing plan artifacts exits 2 with `STEP_FAILED=resume-plan-tail-sentinel`. |
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
| B-invalid-emergency-requested-arg | Invalid `--emergency-requested` exits 2 with a usage error. |
| B-invalid-upstream-repo-arg | Invalid `--upstream-repo` exits 2 with a usage error. |
| Edge-NEVER14 | Static grep on live `scripts/implement-bootstrap.sh` forbids append / `cat` heredoc writes to `session-env.sh`. |
| Edge-breadcrumb-count | stderr capture sees exactly one `→ step0: infra ready` line. |
| Edge-breadcrumb-count-adopt | tracking adoption stderr capture sees exactly one `→ step0: tracking adopted` line. |
| Edge-breadcrumb-count-plan-green | green plan materialization stderr capture emits one branch/log progress line and one `larch:plan` breadcrumb. |
| Edge-breadcrumb-count-plan-summary-fail | summary failure stderr capture emits the branch/log progress line but suppresses the `larch:plan` breadcrumb. |
| B4-all-breadcrumb | widened `DEFERRED=true` `--up-to-phase all` path still emits the coder progress line once on stderr. |
| Edge-breadcrumb-count-coder-green | green coder phase stderr capture emits exactly five `→ step0:` progress lines, including one `coder=cursor` line. |
