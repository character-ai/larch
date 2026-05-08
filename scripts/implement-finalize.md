# scripts/implement-finalize.sh — contract

`scripts/implement-finalize.sh` is the mechanical SSOT for `/implement` Step 8 anchor-fragment write, Step 8a CHANGELOG amend, Step 8b rebase + force-push gate, Steps 14, 15, 16a, and the mechanical part of Step 18. Prompt-only Steps 16 and 17, plus Step 18's external-reviewer warning replay and `--design-only` / `--draft` / `--merge=false` notes, stay in `skills/implement/SKILL.md` so the operator-facing final report remains chat-side.

## Subcommands

- `postbump --state-file PATH --implement-tmpdir PATH [--changelog-bullets-file PATH]` covers Step 8's version-bump-reasoning anchor fragment write, Step 8a's CHANGELOG amend, and Step 8b's rebase + force-push gate. It invokes `scripts/refresh-anchor.sh`, `scripts/check-changelog-present.sh`, `scripts/git-amend-add.sh`, `scripts/rebase-push.sh`, `scripts/check-remote-branch.sh`, and `scripts/git-force-push.sh`, and emits postbump-specific tail records ending with exactly one `STATUS=...` line.
- `postmerge --state-file PATH --final-bail-reason-file PATH` covers Step 14 local cleanup and Step 15 verify-main. It invokes `scripts/local-cleanup.sh` and `scripts/verify-main.sh`, captures their stdout envelopes, forwards their stderr, and emits only Step 14/15 breadcrumbs plus tail records.
- `slack --state-file PATH --final-bail-reason-file PATH` covers Step 16a. It computes `RUN_OUTCOME` with the Step 16a first-match-wins ladder, applies the existing Slack skip gates, invokes `scripts/post-issue-slack.sh` when eligible, and emits `RUN_OUTCOME=`, `SLACK_TS=`, `FINALIZE_SUBCOMMAND=slack`, and `FINALIZE_WARNINGS=`.
- `teardown --state-file PATH --implement-tmpdir PATH` covers the Step 18 title-prefix terminal transition, tmpdir cleanup, tracking-issue URL print, and final `✅ 18` breadcrumb. It invokes `scripts/get-issue-info.sh`, `scripts/round-trip-detect.sh`, `scripts/tracking-issue-write.sh rename`, and, after a basename + session-id sanity check, `scripts/cleanup-tmpdir.sh`.

Exit code `0` is not a complete outcome signal. Consumers must parse `STATUS=` for `postbump`, plus `RUN_OUTCOME=`, `LOCAL_CLEANUP_STATUS=`, `VERIFY_MAIN_STATUS=`, `RENAME_STATUS=`, `SLACK_TS=`, and `FINALIZE_WARNINGS=` for the post-PR subcommands. Exit code `2` is reserved for argument or state-file validation failures.

## State File

The state file is plain `KEY=value` text written once by `skills/implement/SKILL.md` at Step 14 entry. It must live under `/tmp/`, `/private/tmp/`, or `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/`. It is never sourced. `implement-finalize.sh` validates each non-comment, non-blank line against `^[A-Z_][A-Z0-9_]*=.*$` and reads values with `awk`, preserving shell metacharacters literally.

Required keys:

`BRANCH_NAME`, `PR_NUMBER`, `PR_TITLE`, `PR_URL`, `ISSUE_NUMBER`, `REPO`, `DRAFT`, `MERGE`, `SLACK_ENABLED`, `SLACK_AVAILABLE`, `DEFERRED`, `REPO_UNAVAILABLE`, `PR_CLOSED`, `DESIGN_ONLY_DONE`, `BAIL_NEEDS_USER_INPUT`, `STALL_TRACKING`, `DONE_RENAME_APPLIED`.

String keys may be present with empty values except `BRANCH_NAME` when `postmerge` actually attempts local cleanup. Boolean keys must be literal `true` or `false`.

Optional keys:

`STALL_STEP` records the step that set `STALL_TRACKING=true`. Teardown defaults it to `unknown` when absent so older state files remain readable.

`EXPECTED_SESSION_ID` and `EXPECTED_TMPDIR_BASENAME_PREFIX` bind Step 18 cleanup to the session created at Step 0. `EXPECTED_SESSION_ID` is compared to `$IMPLEMENT_TMPDIR/session-id`; when absent (older in-progress state), teardown warns and falls back to basename-only validation. `EXPECTED_TMPDIR_BASENAME_PREFIX` should be `claude-implement-<clone-tag>-`; when absent, teardown derives that prefix from `basename "$PWD"`.

`--final-bail-reason-file` is a path, not the bail text itself. This keeps arbitrary bail prose out of argv and lets Step 16a normalize the detail text to a single 1024-character line only when Slack posting needs it.

## State File for postbump

`postbump` uses a distinct state file, normally `$IMPLEMENT_TMPDIR/postbump-state.sh`, not the post-PR `finalize-state.sh`. It follows the same plain `KEY=value` syntax, tmpdir containment, and no-source parsing rules as the Step 14 state file.

Required keys:

`BRANCH_NAME`, `ISSUE_NUMBER`, `REPO`, `REPO_UNAVAILABLE`, `FORKED_TARGET`, `HAS_BUMP`, `BUMP_TYPE`, `NEW_VERSION`, `BUMP_REASONING_FILE`, `MANIFEST_PATH`, `TOOL_LABEL`, `ANCHOR_COMMENT_ID`.

`HAS_BUMP`, `FORKED_TARGET`, and `REPO_UNAVAILABLE` must be literal `true` or `false`. `BUMP_TYPE` must be `MAJOR`, `MINOR`, `PATCH`, or `NONE`. `BRANCH_NAME` must be non-empty and must not be `main` or `master`; phases that rebase or push also verify the current git branch still matches `BRANCH_NAME`. When `BUMP_TYPE` is not `NONE`, `NEW_VERSION` must match `X.Y.Z`.

`BUMP_REASONING_FILE` is the orchestrator-sanitized version-bump reasoning input, usually `$IMPLEMENT_TMPDIR/anchor-sections-input/version-bump-reasoning-sanitized.md`. `postbump` treats it as session-local trusted input with defense-in-depth guards: it must be a regular non-symlink tmp-path file, its basename must be `version-bump-reasoning-sanitized.md` or match `bump-version-reasoning*.md`, and it must be no larger than 65536 bytes. Invalid reasoning input writes the fallback anchor text and appends a warning to `execution-issues.md` when present.

If `MANIFEST_PATH` is non-empty, `postbump` reads `summary_bullets_categorized` first and falls back to flat `summary_bullets` for the CHANGELOG entry. If `MANIFEST_PATH` is empty, the caller must pass `--changelog-bullets-file PATH` when a bump commit exists and CHANGELOG bullets are available. That file must live under an accepted tmp root, must be regular and non-symlink, and must be no larger than 65536 bytes. Each line may be `Category<TAB>bullet`; bare lines default to `Changed`.

Conflict resume uses the implicit checkpoint file `$IMPLEMENT_TMPDIR/.postbump-phase`, not a CLI flag. `force-push-gate` is the only recognized phase identifier in this release. On a Step 8b rebase conflict that can use the Rebase + Re-bump Sub-procedure, `postbump` writes `force-push-gate` to that file before emitting `STATUS=conflict`. After the sub-procedure returns, the orchestrator re-invokes `postbump` with the same `--state-file` and `--implement-tmpdir`; the script validates the checkpoint and skips directly to the force-push gate. Corrupt, symlinked, oversized, or unknown checkpoint contents fail closed with `STATUS=postbump-state-corrupt`.

## Output Contract

`postbump` prints phase breadcrumbs, then:

```
ANCHOR_REFRESH_STATUS=ok|skipped|failed
CHANGELOG_STATUS=updated|skipped-absent|skipped-fork|skipped-no-bump|skipped-resume|skipped-no-bullets|failed
REBASE_STATUS=rebased|already-fresh|conflict|failed|skipped-resume
FORCE_PUSH_STATUS=pushed|noop_same_ref|absent|skipped-repo-unavailable|failed
RESUME_PHASE=force-push-gate
CALLER_KIND=step8b_rebase
STATUS=ok|skipped|conflict|rebase-failed|push-failed|remote-check-failed|changelog-failed|branch-mismatch|postbump-state-corrupt
FINALIZE_SUBCOMMAND=postbump
FINALIZE_WARNINGS=<N>
```

`RESUME_PHASE=force-push-gate` and `CALLER_KIND=step8b_rebase` are present only on `STATUS=conflict`. The resume phase line is informational; the checkpoint file is authoritative. Consumers MUST parse the last `STATUS=` line. The script emits exactly one `STATUS=...` tail record; future debug output must not emit `STATUS=...` lines.

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

`FINALIZE_WARNINGS` is the count of `**⚠ ...**` warning breadcrumbs printed by that subcommand.

## Behavior Mapping

- `postbump` phase 1 always writes `$IMPLEMENT_TMPDIR/anchor-sections/version-bump-reasoning.md`. It refreshes the tracking anchor when `ISSUE_NUMBER` is non-empty and `REPO_UNAVAILABLE=false`; `ANCHOR_COMMENT_ID` and `REPO` are forwarded when present. Refresh failures are non-fatal and append to `execution-issues.md`.
- `postbump` phase 2 always runs `check-changelog-present.sh`, then skips when CHANGELOG is absent, fork mode is active, no bump skill is available, `BUMP_TYPE=NONE`, or no bullets are available. Otherwise it inserts or replaces `## [NEW_VERSION] - YYYY-MM-DD` in `CHANGELOG.md`, grouping bullets in Keep-a-Changelog order, then amends the bump commit via `git-amend-add.sh`. Changelog read/write/amend failures emit `STATUS=changelog-failed` and stop before rebase.
- `postbump` phase 3 validates the branch and runs `rebase-push.sh --no-push`, adding `--base-remote upstream --base-ref main` in fork mode. Exit 1 writes `$IMPLEMENT_TMPDIR/.postbump-phase` and emits `STATUS=conflict` only for non-fork, repo-available runs; fork and repo-unavailable conflict paths emit `STATUS=rebase-failed`.
- `postbump` phase 4 validates the branch again, skips when `REPO_UNAVAILABLE=true`, otherwise preserves the `check-remote-branch.sh` trichotomy: `present` force-pushes, `absent` leaves initial push to PR creation, and `error` emits `STATUS=remote-check-failed`.
- With `$IMPLEMENT_TMPDIR/.postbump-phase` containing `force-push-gate`, `postbump` skips phases 1-3, runs phase 4 only, and deletes the checkpoint after a successful push/absent/repo-unavailable result.
- Step 14 skips on `DRAFT=true`, then `MERGE!=true`, then a non-empty final-bail-reason file. These skips also force `VERIFY_MAIN_STATUS=skipped`.
- Step 14 cleanup success/partial state comes from `local-cleanup.sh`'s `CLEANUP_SUCCESS`, `CURRENT_BRANCH`, and `BRANCH_DELETED` keys.
- Step 15 runs only after Step 14 actually attempted cleanup. It calls `verify-main.sh --expected-title "$PR_TITLE (#$PR_NUMBER)"`.
- Step 16a `RUN_OUTCOME` order is: `PR_CLOSED=true` → `closed`; `DESIGN_ONLY_DONE=true` → `design-only`; `BAIL_NEEDS_USER_INPUT=true` → `user-input`; non-empty bail file → `blocked`; `MERGE!=true` or `DRAFT=true` → `pr-opened`; fallback → `blocked`.
- Step 18 first checks `ISSUE_NUMBER` is non-empty and `REPO_UNAVAILABLE=false` before any rename branch. Branch A (`STALL_TRACKING=true`) renames to `stalled` only when `get-issue-info.sh --field state` returns exactly `VALUE=OPEN`; empty `VALUE=` remains a silent skip. Branch B renames to `done` when no merge-path done rename has already applied and either `PR_NUMBER` is set or `DESIGN_ONLY_DONE=true`. Branch C is a no-op.
- Before any Branch A/B rename, Step 18 fetches **both** the issue title and body with `gh issue view "$issue" --repo "$REPO" --json title,body --jq '"TITLE=\(.title // "")\n" + (.body // "")'`, splitting the response into the leading `TITLE=` line and the remaining body (written to a temp file under `--implement-tmpdir` when available), then runs `scripts/round-trip-detect.sh --text-string "$title" --text-file <body-file>` and passes `--round-trip true|false` to `tracking-issue-write.sh rename`. If `REPO` is empty in the state file, teardown first tries `scripts/resolve-repo.sh`; only if that fails does it preserve the prior ambient-repo fallback and emit a warning that `gh issue view` ran without `--repo`. The `--repo` flag matches the rename call's repo scope so transient `gh repo set-default` / cwd disagreements cannot fetch the wrong issue (post-review FINDING_F2). Detection is best-effort: fetch failure, missing detector, detector failure, or missing `ROUND_TRIP=` output logs `Step 18: round-trip detection skipped: <reason>` and defaults to `false`; the lifecycle rename still runs. Detector stderr is **not** redirected — `warn_false` diagnostics surface so degraded paths are visible to operators (post-review FINDING_F3). Sticky preservation of an existing marker is owned by `tracking-issue-write.sh`.
- On stalled runs (`STALL_TRACKING=true`), Step 18 then probes the repo root with `git rev-parse --show-toplevel`. If `git status --porcelain` is non-empty, it best-effort stashes tracked and untracked edits with a `larch-stalled-<issue>-<step> <utc>` label and records the newest stash ref. Stash failures produce a warning and do not block teardown.
- On stalled runs, Step 18 writes `<git-dir>/larch-stalled-run.txt` atomically with `ISSUE_NUMBER=`, `ISSUE_URL=`, `STALL_STEP=`, `STASH_REF=`, and `TIMESTAMP=`. It resolves `<git-dir>` via `git rev-parse --git-dir` so worktree-style gitdirs are supported. Sentinel write failures produce a warning and do not block teardown.
- Before invoking `cleanup-tmpdir.sh`, teardown writes `$IMPLEMENT_TMPDIR/.run-cleaned-up` best-effort to release the post-/design Stop hook for legitimate end-of-run paths. The write is intentionally before `verify_cleanup_target`, so a refused cleanup still releases the Stop hook; operator cleanup of the leaked tmpdir remains manual. Teardown then verifies that `basename "$IMPLEMENT_TMPDIR"` starts with `EXPECTED_TMPDIR_BASENAME_PREFIX` and that `$IMPLEMENT_TMPDIR/session-id` matches `EXPECTED_SESSION_ID` when one is present. On mismatch, it appends a best-effort Tool Failures entry to `$IMPLEMENT_TMPDIR/execution-issues.md`, prints `**⚠ 18: cleanup target failed sanity check (basename=<x>, session-id-match=<y/n>) — refusing to rm-rf. Operator must clean manually.**`, skips cleanup, and continues URL printing plus the final breadcrumb. `cleanup-tmpdir.sh` runs after this sanity check, after stalled-run auto-stash/sentinel work, and before the tracking-issue URL print. `teardown` reads all state-file values before cleanup and resolves the issue URL before cleanup so the stalled-run sentinel can carry it.
- After the tracking-issue URL print and immediately before the final `✅ 18: cleanup — implement complete!` breadcrumb, teardown emits a best-effort closing `token-ledger.sh mark "Step 18 — done"` and `timing-ledger.sh mark "Step 18 — done"` pair (both redirected to `/dev/null` on stdout/stderr; both `|| true`). The cap fixes a token-attribution edge: `scripts/token-report.sh` `vendor_table` slices the LAST mark with `$end == null`, so without a closing mark, vendor records logged after Step 18 in the same JSONL ledger (most plausibly from a subsequent `/implement` run whose launcher falls back to `pwd | sha256_hex` in `token-ledger.sh resolve_session_id()` and writes to the same shared `larch-tokens-<pwd-hash>.jsonl` file) accrue to the prior run's `Step 18 — cleanup` bucket. The orchestrator-side `skills/implement/SKILL.md` Step 18 terminal Bash block emits the same closing-mark pair as defense-in-depth so at least one of the two fires on degraded paths where the other is skipped (e.g., a Stop hook that interrupts the orchestrator's terminal Bash, or an early-exit teardown skip).

## Invariants

- The state file is never sourced.
- Leaf-script stdout is captured and parsed; leaf-script stderr passes through to the operator.
- All leaf-script failures are best-effort except invocation/state validation. They surface through warning breadcrumbs and tail records, not non-zero exits.
- `--implement-tmpdir` and `--state-file` must be under `/tmp/`, `/private/tmp/`, or the larch cache sessions root.
- Round-trip detection never sends issue bodies through argv; bodies are file-backed per `scripts/round-trip-detect.md`.
- post-Step-11 subcommands (`postmerge`, `slack`, `teardown`) MUST NOT append to `$IMPLEMENT_TMPDIR/execution-issues.md` because Step 11 has already published the anchor and Step 18 deletes the tmpdir. Pre-Step-11 subcommands (`postbump`) MAY append warnings to `$IMPLEMENT_TMPDIR/execution-issues.md`; Step 11 mirrors them into the tracking-issue anchor.
- The literal phase identifier `force-push-gate`, the contents of `$IMPLEMENT_TMPDIR/.postbump-phase`, is reproduced byte-identically in `skills/implement/SKILL.md` Step 8 conflict-resume prose. Changes to the recognized-phase enum here require a paired SKILL.md update.
- The orchestrator MUST parse the last `STATUS=` line in `postbump` stdout. The script emits exactly one `STATUS=...` line as part of the trailing tail records; future debug output is not permitted to emit `STATUS=...` lines.

## Primary Callers

- `skills/implement/SKILL.md` Step 8 writes the postbump state file and invokes `postbump`.
- `skills/implement/SKILL.md` Step 14 entry writes the state file and invokes `postmerge`.
- `skills/implement/SKILL.md` Step 16a invokes `slack`.
- `skills/implement/SKILL.md` Step 18 invokes `teardown`.

## Test Harness

`scripts/test-implement-finalize.sh` is the offline regression harness. It copies this script into a `/tmp` sandbox with stub sibling helpers and git/gh shims, exercises all four subcommands, postbump changelog/category/checkpoint/error paths, round-trip detection pass-through/default-false behavior, stalled-run stash/sentinel handling, `.run-cleaned-up` Stop-hook release behavior before cleanup validation, and state-file parsing, normalizes elapsed-time parentheticals, and is wired through `make test-implement-finalize`. `scripts/test-finalize-sanity-check.sh` covers the Step 18 cleanup target sanity check specifically.

## Edit In Sync

When changing this script, update this contract, `skills/implement/SKILL.md` Steps 8, 8a, 8b, and 14-18, `scripts/test-implement-finalize.sh`, `scripts/test-implement-finalize.md`, `.claude/skills/bump-version/SKILL.md`, `skills/implement/references/rebase-rebump-subprocedure.md`, `SECURITY.md`, `Makefile`, and the harness table in `docs/linting.md` if the public target or coverage changes.
