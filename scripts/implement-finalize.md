# scripts/implement-finalize.sh — contract

`scripts/implement-finalize.sh` is the mechanical SSOT for `/implement` Steps 14, 15, 16a, and the mechanical part of Step 18. Prompt-only Steps 16 and 17, plus Step 18's external-reviewer warning replay and `--design-only` / `--draft` / `--merge=false` notes, stay in `skills/implement/SKILL.md` so the operator-facing final report remains chat-side.

## Subcommands

- `postmerge --state-file PATH --final-bail-reason-file PATH` covers Step 14 local cleanup and Step 15 verify-main. It invokes `scripts/local-cleanup.sh` and `scripts/verify-main.sh`, captures their stdout envelopes, forwards their stderr, and emits only Step 14/15 breadcrumbs plus tail records.
- `slack --state-file PATH --final-bail-reason-file PATH` covers Step 16a. It computes `RUN_OUTCOME` with the Step 16a first-match-wins ladder, applies the existing Slack skip gates, invokes `scripts/post-issue-slack.sh` when eligible, and emits `RUN_OUTCOME=`, `SLACK_TS=`, `FINALIZE_SUBCOMMAND=slack`, and `FINALIZE_WARNINGS=`.
- `teardown --state-file PATH --implement-tmpdir PATH` covers the Step 18 title-prefix terminal transition, tmpdir cleanup, tracking-issue URL print, and final `✅ 18` breadcrumb. It invokes `scripts/get-issue-info.sh`, `scripts/round-trip-detect.sh`, `scripts/tracking-issue-write.sh rename`, and, after a basename + session-id sanity check, `scripts/cleanup-tmpdir.sh`.

Exit code `0` is not a complete outcome signal. Consumers must parse `RUN_OUTCOME=`, `LOCAL_CLEANUP_STATUS=`, `VERIFY_MAIN_STATUS=`, `RENAME_STATUS=`, `SLACK_TS=`, and `FINALIZE_WARNINGS=` to detect Slack, cleanup, rename, and verify-main failures. Exit code `2` is reserved for argument or state-file validation failures.

## State File

The state file is plain `KEY=value` text written once by `skills/implement/SKILL.md` at Step 14 entry. It must live under `/tmp/`, `/private/tmp/`, or `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/`. It is never sourced. `implement-finalize.sh` validates each non-comment, non-blank line against `^[A-Z_][A-Z0-9_]*=.*$` and reads values with `awk`, preserving shell metacharacters literally.

Required keys:

`BRANCH_NAME`, `PR_NUMBER`, `PR_TITLE`, `PR_URL`, `ISSUE_NUMBER`, `REPO`, `DRAFT`, `MERGE`, `SLACK_ENABLED`, `SLACK_AVAILABLE`, `DEFERRED`, `REPO_UNAVAILABLE`, `PR_CLOSED`, `DESIGN_ONLY_DONE`, `BAIL_NEEDS_USER_INPUT`, `STALL_TRACKING`, `DONE_RENAME_APPLIED`.

String keys may be present with empty values except `BRANCH_NAME` when `postmerge` actually attempts local cleanup. Boolean keys must be literal `true` or `false`.

Optional keys:

`STALL_STEP` records the step that set `STALL_TRACKING=true`. Teardown defaults it to `unknown` when absent so older state files remain readable.

`EXPECTED_SESSION_ID` and `EXPECTED_TMPDIR_BASENAME_PREFIX` bind Step 18 cleanup to the session created at Step 0. `EXPECTED_SESSION_ID` is compared to `$IMPLEMENT_TMPDIR/session-id`; when absent (older in-progress state), teardown warns and falls back to basename-only validation. `EXPECTED_TMPDIR_BASENAME_PREFIX` should be `claude-implement-<clone-tag>-`; when absent, teardown derives that prefix from `basename "$PWD"`.

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
STASH_REF=<stash-ref-or-empty>
SENTINEL_WRITTEN=true|false
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
- Before any Branch A/B rename, Step 18 fetches **both** the issue title and body with `gh issue view "$issue" --repo "$REPO" --json title,body --jq '"TITLE=\(.title // "")\n" + (.body // "")'`, splitting the response into the leading `TITLE=` line and the remaining body (written to a temp file under `--implement-tmpdir` when available), then runs `scripts/round-trip-detect.sh --text-string "$title" --text-file <body-file>` and passes `--round-trip true|false` to `tracking-issue-write.sh rename`. If `REPO` is empty in the state file, teardown first tries `scripts/resolve-repo.sh`; only if that fails does it preserve the prior ambient-repo fallback and emit a warning that `gh issue view` ran without `--repo`. The `--repo` flag matches the rename call's repo scope so transient `gh repo set-default` / cwd disagreements cannot fetch the wrong issue (post-review FINDING_F2). Detection is best-effort: fetch failure, missing detector, detector failure, or missing `ROUND_TRIP=` output logs `Step 18: round-trip detection skipped: <reason>` and defaults to `false`; the lifecycle rename still runs. Detector stderr is **not** redirected — `warn_false` diagnostics surface so degraded paths are visible to operators (post-review FINDING_F3). Sticky preservation of an existing marker is owned by `tracking-issue-write.sh`.
- On stalled runs (`STALL_TRACKING=true`), Step 18 then probes the repo root with `git rev-parse --show-toplevel`. If `git status --porcelain` is non-empty, it best-effort stashes tracked and untracked edits with a `larch-stalled-<issue>-<step> <utc>` label and records the newest stash ref. Stash failures produce a warning and do not block teardown.
- On stalled runs, Step 18 writes `<git-dir>/larch-stalled-run.txt` atomically with `ISSUE_NUMBER=`, `ISSUE_URL=`, `STALL_STEP=`, `STASH_REF=`, and `TIMESTAMP=`. It resolves `<git-dir>` via `git rev-parse --git-dir` so worktree-style gitdirs are supported. Sentinel write failures produce a warning and do not block teardown.
- Before invoking `cleanup-tmpdir.sh`, teardown writes `$IMPLEMENT_TMPDIR/.run-cleaned-up` best-effort to release the post-/design Stop hook for legitimate end-of-run paths. The write is intentionally before `verify_cleanup_target`, so a refused cleanup still releases the Stop hook; operator cleanup of the leaked tmpdir remains manual. Teardown then verifies that `basename "$IMPLEMENT_TMPDIR"` starts with `EXPECTED_TMPDIR_BASENAME_PREFIX` and that `$IMPLEMENT_TMPDIR/session-id` matches `EXPECTED_SESSION_ID` when one is present. On mismatch, it appends a best-effort Tool Failures entry to `$IMPLEMENT_TMPDIR/execution-issues.md`, prints `**⚠ 18: cleanup target failed sanity check (basename=<x>, session-id-match=<y/n>) — refusing to rm-rf. Operator must clean manually.**`, skips cleanup, and continues URL printing plus the final breadcrumb. `cleanup-tmpdir.sh` runs after this sanity check, after stalled-run auto-stash/sentinel work, and before the tracking-issue URL print. `teardown` reads all state-file values before cleanup and resolves the issue URL before cleanup so the stalled-run sentinel can carry it.

## Invariants

- The state file is never sourced.
- Leaf-script stdout is captured and parsed; leaf-script stderr passes through to the operator.
- All leaf-script failures are best-effort except invocation/state validation. They surface through warning breadcrumbs and tail records, not non-zero exits.
- `--implement-tmpdir` and `--state-file` must be under `/tmp/`, `/private/tmp/`, or the larch cache sessions root.
- Round-trip detection never sends issue bodies through argv; bodies are file-backed per `scripts/round-trip-detect.md`.

## Primary Callers

- `skills/implement/SKILL.md` Step 14 entry writes the state file and invokes `postmerge`.
- `skills/implement/SKILL.md` Step 16a invokes `slack`.
- `skills/implement/SKILL.md` Step 18 invokes `teardown`.

## Test Harness

`scripts/test-implement-finalize.sh` is the offline regression harness. It copies this script into a `/tmp` sandbox with stub sibling helpers and git/gh shims, exercises all three subcommands, round-trip detection pass-through/default-false behavior, stalled-run stash/sentinel handling, `.run-cleaned-up` Stop-hook release behavior before cleanup validation, and state-file parsing, normalizes elapsed-time parentheticals, and is wired through `make test-implement-finalize`. `scripts/test-finalize-sanity-check.sh` covers the Step 18 cleanup target sanity check specifically.

## Edit In Sync

When changing this script, update this contract, `skills/implement/SKILL.md` Steps 14-18, `scripts/test-implement-finalize.sh`, `Makefile`, and the harness table in `docs/linting.md` if the public target or coverage changes.
