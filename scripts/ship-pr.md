# ship-pr.sh

`scripts/ship-pr.sh` is the mechanical state machine for the post-review tail of `/implement`: relevant checks, version bump, PR body/create, CI polling/fix dispatch, merge, postmerge finalization, and teardown.

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

The script also writes `$IMPLEMENT_TMPDIR/postbump-state.sh` before `implement-finalize.sh postbump` and `$IMPLEMENT_TMPDIR/finalize-state.sh` before postmerge/teardown.

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
- Fork mode skips bump application and uses direct `rebase-push.sh --base-remote upstream --base-ref main`.
- State writes use `tmp.$$` plus `mv`.

## Postmerge Summary Comments

`run_postmerge_phase` posts `larch:token-report` and `larch:final-summary` tracking-issue comments before teardown, rehydrating `LARCH_TOKEN_SESSION_ID`/`LARCH_CLAUDE_SOURCE_FILE` from `$IMPLEMENT_TMPDIR/session-env.sh`. The upserts are skipped when `FORKED_TARGET=true`, `ISSUE_NUMBER` is empty, or `REPO_UNAVAILABLE=true`. `advance_phase "done"` runs before teardown so the state file is updated while it still exists; the function ends with `exit 0` to bypass the state-machine loop after teardown removes the state file.

## Harness

`scripts/test-ship-pr.sh` runs offline state/transition coverage with stubbed helpers. It is wired through `make test-ship-pr`.

## Edit In Sync

When changing phase names, exit-code meaning, helper stdout parsing, or state keys, update `skills/implement/SKILL.md`, `scripts/test-ship-pr.sh`, `scripts/test-implement-structure.sh`, and this file together.
