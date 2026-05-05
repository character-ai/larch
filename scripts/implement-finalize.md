# scripts/implement-finalize.sh — contract

`scripts/implement-finalize.sh` is the mechanical SSOT for `/implement` Steps 14, 15, 16a, and the mechanical part of Step 18. Prompt-only Steps 16 and 17, plus Step 18's external-reviewer warning replay and `--design-only` / `--draft` / `--merge=false` notes, stay in `skills/implement/SKILL.md` so the operator-facing final report remains chat-side.

## Subcommands

- `postmerge --state-file PATH --final-bail-reason-file PATH` covers Step 14 local cleanup and Step 15 verify-main. It invokes `scripts/local-cleanup.sh` and `scripts/verify-main.sh`, captures their stdout envelopes, forwards their stderr, and emits only Step 14/15 breadcrumbs plus tail records.
- `slack --state-file PATH --final-bail-reason-file PATH` covers Step 16a. It computes `RUN_OUTCOME` with the Step 16a first-match-wins ladder, applies the existing Slack skip gates, invokes `scripts/post-issue-slack.sh` when eligible, and emits `RUN_OUTCOME=`, `SLACK_TS=`, `FINALIZE_SUBCOMMAND=slack`, and `FINALIZE_WARNINGS=`.
- `teardown --state-file PATH --implement-tmpdir PATH` covers the Step 18 title-prefix terminal transition, tmpdir cleanup, tracking-issue URL print, and final `✅ 18` breadcrumb. It invokes `scripts/get-issue-info.sh`, `scripts/tracking-issue-write.sh rename`, and `scripts/cleanup-tmpdir.sh`.

Exit code `0` is not a complete outcome signal. Consumers must parse `RUN_OUTCOME=`, `LOCAL_CLEANUP_STATUS=`, `VERIFY_MAIN_STATUS=`, `RENAME_STATUS=`, `SLACK_TS=`, and `FINALIZE_WARNINGS=` to detect Slack, cleanup, rename, and verify-main failures. Exit code `2` is reserved for argument or state-file validation failures.

## State File

The state file is plain `KEY=value` text written once by `skills/implement/SKILL.md` at Step 14 entry. It must live under `/tmp/` or `/private/tmp/`. It is never sourced. `implement-finalize.sh` validates each non-comment, non-blank line against `^[A-Z_][A-Z0-9_]*=.*$` and reads values with `awk`, preserving shell metacharacters literally.

Required keys:

`BRANCH_NAME`, `PR_NUMBER`, `PR_TITLE`, `PR_URL`, `ISSUE_NUMBER`, `REPO`, `DRAFT`, `MERGE`, `SLACK_ENABLED`, `SLACK_AVAILABLE`, `DEFERRED`, `REPO_UNAVAILABLE`, `PR_CLOSED`, `DESIGN_ONLY_DONE`, `BAIL_NEEDS_USER_INPUT`, `STALL_TRACKING`, `DONE_RENAME_APPLIED`.

String keys may be present with empty values except `BRANCH_NAME` when `postmerge` actually attempts local cleanup. Boolean keys must be literal `true` or `false`.

`--final-bail-reason-file` is a path, not the bail text itself. This keeps arbitrary bail prose out of argv and lets Step 16a normalize the detail text to a single 1024-character line only when Slack posting needs it.

## Output Contract

`postmerge` prints one Step 14 breadcrumb, optionally one Step 15 breadcrumb, then:

```
LOCAL_CLEANUP_STATUS=success|partial|skipped-draft|skipped-merge-false|skipped-bail
VERIFY_MAIN_STATUS=verified|unexpected|skipped
FINALIZE_SUBCOMMAND=postmerge
FINALIZE_WARNINGS=<N>
```

`slack` prints one Step 16a breadcrumb for skip, success, or failure, then:

```
RUN_OUTCOME=closed|pr-opened|design-only|blocked|user-input
SLACK_TS=<value-or-empty>
FINALIZE_SUBCOMMAND=slack
FINALIZE_WARNINGS=<N>
```

`teardown` prints the tracking issue URL when resolvable, then the final Step 18 breadcrumb, then:

```
RENAME_BRANCH=A|B|C|skipped
RENAME_STATUS=ok|failed|skipped
ISSUE_URL=<value-or-empty>
FINALIZE_SUBCOMMAND=teardown
FINALIZE_WARNINGS=<N>
```

`FINALIZE_WARNINGS` is the count of `**⚠ ...**` warning breadcrumbs printed by that subcommand. Finalizer-time issues are stdout-only telemetry; this script must not append to `execution-issues.md`, because Step 11 has already published the anchor and Step 18 deletes the tmpdir.

## Behavior Mapping

- Step 14 skips on `DRAFT=true`, then `MERGE!=true`, then a non-empty final-bail-reason file. These skips also force `VERIFY_MAIN_STATUS=skipped`.
- Step 14 cleanup success/partial state comes from `local-cleanup.sh`'s `CLEANUP_SUCCESS`, `CURRENT_BRANCH`, and `BRANCH_DELETED` keys.
- Step 15 runs only after Step 14 actually attempted cleanup. It calls `verify-main.sh --expected-title "$PR_TITLE (#$PR_NUMBER)"`.
- Step 16a `RUN_OUTCOME` order is: `PR_CLOSED=true` → `closed`; `DESIGN_ONLY_DONE=true` → `design-only`; `BAIL_NEEDS_USER_INPUT=true` → `user-input`; non-empty bail file → `blocked`; `MERGE!=true` or `DRAFT=true` → `pr-opened`; fallback → `blocked`.
- Step 18 first checks `ISSUE_NUMBER` is non-empty and `REPO_UNAVAILABLE=false` before any rename branch. Branch A (`STALL_TRACKING=true`) renames to `stalled` only when `get-issue-info.sh --field state` returns exactly `VALUE=OPEN`; empty `VALUE=` remains a silent skip. Branch B renames to `done` when no merge-path done rename has already applied and either `PR_NUMBER` is set or `DESIGN_ONLY_DONE=true`. Branch C is a no-op.
- `cleanup-tmpdir.sh` runs before the tracking-issue URL print. `teardown` reads all state-file values before cleanup, then uses in-memory `ISSUE_NUMBER` for the post-cleanup URL lookup.

## Invariants

- The state file is never sourced.
- Leaf-script stdout is captured and parsed; leaf-script stderr passes through to the operator.
- All leaf-script failures are best-effort except invocation/state validation. They surface through warning breadcrumbs and tail records, not non-zero exits.
- `--implement-tmpdir` and `--state-file` must be under `/tmp/` or `/private/tmp/`.

## Primary Callers

- `skills/implement/SKILL.md` Step 14 entry writes the state file and invokes `postmerge`.
- `skills/implement/SKILL.md` Step 16a invokes `slack`.
- `skills/implement/SKILL.md` Step 18 invokes `teardown`.

## Test Harness

`scripts/test-implement-finalize.sh` is the offline regression harness. It copies this script into a `/tmp` sandbox with stub sibling helpers, exercises all three subcommands and state-file parsing, normalizes elapsed-time parentheticals, and is wired through `make test-implement-finalize`.

## Edit In Sync

When changing this script, update this contract, `skills/implement/SKILL.md` Steps 14-18, `scripts/test-implement-finalize.sh`, `Makefile`, and the harness table in `docs/linting.md` if the public target or coverage changes.
