# ship-pr.sh

`scripts/ship-pr.sh` is the mechanical state machine for the post-review tail of `/implement`: relevant checks, version bump, PR body/create, CI polling/fix dispatch, merge, and postmerge finalization (local cleanup + verify-main). Teardown, token-report refresh, and final tracking-issue summary are owned by the prompt-side Step 18 orchestrator, which runs after ship-pr.sh exits with `PHASE=done`.

## Interface

```text
ship-pr.sh --state-file PATH --implement-tmpdir PATH --merge true|false --draft true|false --forked true|false --repo OWNER/REPO [--auto-mode true|false] [--no-admin-fallback true|false] [--resume-phase PHASE]
```

`--state-file` must live under `--implement-tmpdir`. If the state file does not exist, the script writes an initial uppercase-key state file atomically.

## State

`ship-pr-state.sh` is plain `KEY=value` text and is never sourced. Required keys include `PHASE`, branch/repo/issue identity, PR fields, bump fields, CI counters, checkpoint fields, and finalizer fields. Every non-comment line must match `^[A-Z_][A-Z0-9_]*=.*$`.

Checkpoint phases:

- `checks`
- `bump`
- `pr-prep`
- `pr-create`
- `ci-initial`
- `ci-merge`
- `evaluate-failure`
- `postmerge`
- `done`

The script also writes `$IMPLEMENT_TMPDIR/postbump-state.sh` before `implement-finalize.sh postbump` and `$IMPLEMENT_TMPDIR/finalize-state.sh` before `postmerge`.

## Exit Codes

- `0` means complete or a prompt-side checkpoint (`OOS_PENDING=true` or `CI_PASSED=true`).
- `3` means the CI loop needs user input. `BAIL_REASON` and `BAIL_NEEDS_USER_INPUT=true` are written to state.
- `4` means stalled cleanup. `STALL_TRACKING=true` and `STALL_STEP` are written to state.
- `5` means the prompt-side Rebase + Re-bump Sub-procedure must run. `RESUME_PHASE` and `CALLER_KIND` are written to state.

## Helper Contracts

`ship-pr.sh` parses stdout envelopes from existing helpers rather than relying only on exit status:

- `run-relevant-checks-captured.sh` success requires `RELEVANT_CHECKS_OK=true`.
- `implement-finalize.sh postbump` uses the last `STATUS=` line.
- `create-pr.sh` emits `PR_NUMBER`, `PR_URL`, `PR_TITLE`, and `PR_STATUS`; existing PRs trigger `gh-pr-body-update.sh`.
- `ci-wait.sh` emits `ACTION`, counters, `FAILED_RUN_ID`, and `BAIL_REASON`.
- `merge-pr.sh` emits `MERGE_RESULT` and `ERROR`.

## Invariants

- Postbump conflict preserves `CALLER_KIND=step8b_rebase`.
- `ci-initial` treats `ACTION=merge` as CI passed and exits `0`; `ci-merge` treats it as permission to call `merge-pr.sh`.
- At the start of `ci-merge` phase (after the `REPO_UNAVAILABLE` early-return block), ship-pr.sh calls `larch-log.sh commit --skill implement --run-id <RUN_ID>` (best-effort) to flush pending larch-log writes before merge. This covers `version-bump-reasoning`, `oos-issues`, `run-statistics`, `token-report`, `timing-report`, and `execution-issues` batches written after the pre-bump log flush. The rebase-rebump sub-procedure step 1b performs the same flush on any rebase path; this covers the happy path where no rebase was needed. The commit is pushed so it lands in the PR before `merge-pr.sh` is called; push failure is non-fatal.
- Fork mode skips bump application and uses direct `rebase-push.sh --base-remote upstream --base-ref main`.
- State writes use `tmp.$$` plus `mv`.

## Postmerge Phase

`run_postmerge_phase` calls `implement-finalize.sh postmerge` (Steps 14+15: local cleanup and verify-main), then calls `advance_phase "done"` and exits 0. Token-report refresh, `larch:final-summary` upsert, session-transcript commit, manifest finalization, and tmpdir teardown all run in the prompt-side Step 18 orchestrator after ship-pr.sh exits with `PHASE=done`; `$IMPLEMENT_TMPDIR` remains intact for Step 18 to use.

## Harness

`scripts/test-ship-pr.sh` runs offline state/transition coverage with stubbed helpers. It is wired through `make test-ship-pr`.

## Edit In Sync

When changing phase names, exit-code meaning, helper stdout parsing, or state keys, update `skills/implement/SKILL.md`, `scripts/test-ship-pr.sh`, `scripts/test-implement-structure.sh`, and this file together.
