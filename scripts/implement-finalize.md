# scripts/implement-finalize.sh — contract

`scripts/implement-finalize.sh` is the mechanical SSOT for `/implement` Step 8 version-bump-reasoning log write, Step 8a CHANGELOG commit, Step 8b rebase + force-push gate, Steps 14, 15, and the mechanical part of Step 18. Prompt-only Steps 16 and 17, plus Step 18's external-reviewer warning replay and `--design-only` / `--draft` / `--merge=false` notes, stay in `skills/implement/SKILL.md` so the operator-facing final report remains chat-side.

## Subcommands

- `postbump --state-file PATH --implement-tmpdir PATH [--changelog-bullets-file PATH]` covers Step 8's version-bump-reasoning version-bump-reasoning log write, Step 8a's CHANGELOG commit, and Step 8b's rebase + force-push gate. It invokes `scripts/larch-log.sh`, `scripts/check-changelog-present.sh`, `scripts/commit-changelog.sh`, `scripts/rebase-push.sh`, `scripts/check-remote-branch.sh`, and `scripts/git-force-push.sh`, and emits postbump-specific tail records ending with exactly one `STATUS=...` line.
- `postmerge --state-file PATH --final-bail-reason-file PATH` covers Step 14 local cleanup and Step 15 verify-main. It invokes `scripts/local-cleanup.sh` and `scripts/verify-main.sh`, captures their stdout envelopes, forwards their stderr, and emits only Step 14/15 breadcrumbs plus tail records.
- `teardown --state-file PATH --implement-tmpdir PATH` covers the Step 18 title-prefix terminal transition, manifest finalization, tmpdir cleanup, tracking-issue URL print, and final `✅ 18` compact breadcrumb. It invokes `scripts/larch-log.sh manifest --log-root "$IMPLEMENT_TMPDIR/larch-logs"` best-effort to set `stalled_at_step` on stall paths (and `status=partial` plus `recovery_reason` only on manifest-loss recovery), `scripts/get-issue-info.sh`, `scripts/tracking-issue-write.sh rename`, and, after a basename + session-id sanity check, `scripts/cleanup-tmpdir.sh`. It does not create a dedicated larch-log flush commit; log commits are produced by explicit lifecycle flush points before teardown.

Exit code `0` is not a complete outcome signal. Consumers must parse `STATUS=` for `postbump`, plus `LOCAL_CLEANUP_STATUS=`, `VERIFY_MAIN_STATUS=`, `RENAME_STATUS=`, and `FINALIZE_WARNINGS=` for the post-PR subcommands. Exit code `2` is reserved for argument or state-file validation failures.

## State File

The state file is plain `KEY=value` text written by `scripts/ship-pr.sh` before postmerge and restored by `scripts/restore-finalize-state.sh` immediately before teardown. It must live under `/tmp/`, `/private/tmp/`, `/var/folders/` (macOS), or `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/`. It is never sourced. `implement-finalize.sh` validates each non-comment, non-blank line against `^[A-Z_][A-Z0-9_]*=.*$` and reads values with `awk`, preserving shell metacharacters literally.

Required keys:

`BRANCH_NAME`, `PR_NUMBER`, `PR_TITLE`, `PR_URL`, `ISSUE_NUMBER`, `REPO`, `DRAFT`, `MERGE`, `DEFERRED`, `REPO_UNAVAILABLE`, `PR_CLOSED`, `DESIGN_ONLY_DONE`, `BAIL_NEEDS_USER_INPUT`, `STALL_TRACKING`, `DONE_RENAME_APPLIED`.

String keys may be present with empty values except `BRANCH_NAME` when `postmerge` actually attempts local cleanup. Boolean keys must be literal `true` or `false`.

Optional keys:

`STALL_STEP` records the step that set `STALL_TRACKING=true`. Teardown defaults it to `unknown` when absent so older state files remain readable.

`EXPECTED_SESSION_ID` and `EXPECTED_TMPDIR_BASENAME_PREFIX` bind Step 18 cleanup to the session created at Step 0. `EXPECTED_SESSION_ID` is compared to `$IMPLEMENT_TMPDIR/session-id`; when absent (older in-progress state), teardown warns and falls back to basename-only validation. `EXPECTED_TMPDIR_BASENAME_PREFIX` should be `claude-implement-<clone-tag>-`; when absent, teardown derives that prefix from `basename "$PWD"`.

`--final-bail-reason-file` is a path, not the bail text itself. This keeps arbitrary bail prose out of argv.

## State File for postbump

`postbump` uses a distinct state file, normally `$IMPLEMENT_TMPDIR/postbump-state.sh`, not the post-PR `finalize-state.sh`. It follows the same plain `KEY=value` syntax, tmpdir containment, and no-source parsing rules as the Step 14 state file.

Required keys:

`BRANCH_NAME`, `ISSUE_NUMBER`, `PR_TITLE`, `REPO`, `REPO_UNAVAILABLE`, `FORKED_TARGET`, `HAS_BUMP`, `BUMP_TYPE`, `NEW_VERSION`, `BUMP_REASONING_FILE`, `MANIFEST_PATH`, `TOOL_LABEL`.

`HAS_BUMP`, `FORKED_TARGET`, and `REPO_UNAVAILABLE` must be literal `true` or `false`. `BUMP_TYPE` must be `MAJOR`, `MINOR`, `PATCH`, or `NONE`. `BRANCH_NAME` must be non-empty and must not be `main` or `master`; phases that rebase or push also verify the current git branch still matches `BRANCH_NAME`. `PR_TITLE` must be present in the state file but may be empty. When `BUMP_TYPE` is not `NONE`, `NEW_VERSION` must match `X.Y.Z`.

`BUMP_REASONING_FILE` is the orchestrator-sanitized version-bump reasoning input, usually `$IMPLEMENT_TMPDIR/larch-log-batches-input/version-bump-reasoning-sanitized.md`. `postbump` treats it as session-local trusted input with defense-in-depth guards: it must be a regular non-symlink tmp-path file, its basename must be `version-bump-reasoning-sanitized.md` or match `bump-version-reasoning*.md`, and it must be no larger than 65536 bytes. Invalid reasoning input writes the fallback log fallback text and appends a warning to `execution-issues.md` when present. Before calling `larch-log.sh write`, `postbump` pipes the content through `awk` to collapse any multiple consecutive blank lines into one and strip trailing blank lines, preventing MD012 violations in the committed batch file.

If `MANIFEST_PATH` is non-empty, `postbump` reads `summary_bullets_categorized` first and falls back to flat `summary_bullets` when the manifest parses as JSON but lacks categorized bullets. If `MANIFEST_PATH` is empty, the caller may pass `--changelog-bullets-file PATH`; that file must live under an accepted tmp root, must be regular and non-symlink, and must be no larger than 65536 bytes. Each line may be `Category<TAB>bullet`; bare lines default to `Changed`. When Step 8a finds no bullets, it either synthesizes `Closed: #<issue>` with an optional `PR_TITLE` suffix when fallback context is available, skips with `CHANGELOG_STATUS=skipped-no-bullets` for non-JSON manifest input, or fails with `CHANGELOG_STATUS=fail-no-manifest-no-issue`; only that last branch appends an `execution-issues.md` note containing `manifest_path='<value>'`, `manifest_exists=<true|false>`, and `coder='<TOOL_LABEL>'`.

Conflict resume uses the implicit checkpoint file `$IMPLEMENT_TMPDIR/.postbump-phase`, not a CLI flag. `force-push-gate` is the only recognized phase identifier in this release. On a Step 8b rebase conflict that can use the Rebase + Re-bump Sub-procedure, `postbump` writes `force-push-gate` to that file before emitting `STATUS=conflict`. After the sub-procedure returns, the orchestrator re-invokes `postbump` with the same `--state-file` and `--implement-tmpdir`; the script validates the checkpoint and skips directly to the force-push gate. Corrupt, symlinked, oversized, or unknown checkpoint contents fail closed with `STATUS=postbump-state-corrupt`.

## Output Contract

Step-boundary completion and skip breadcrumbs emitted by this script use `/implement`'s compact key/value format:

```
<icon> <step>: <short-name> status=<complete|skip|bypass> [reason=<token>] [outcome=<token>] [sha=<hash>] elapsed=<time>
```

Warnings remain prose-format `**⚠ ...**` lines. Tail records remain `KEY=value` lines and are not breadcrumbs.

During `postbump`, the script first refreshes `version-bump-reasoning.md`, then best-effort calls `larch-log.sh commit` (gated on `LARCH_NO_LOGS_COMMIT != true`) to commit that batch and any other updated log files onto the PR branch, and only then emits the compact Step 8 `larch-log` breadcrumb. This preserves the batch even when the Step 7a pre-bump flush was the last commit before bump:

```
LOG_WRITE_STATUS=ok|skipped|failed
CHANGELOG_STATUS=updated|skipped-absent|skipped-fork|skipped-no-bump|skipped-no-bullets|skipped-resume|fail-no-manifest-no-issue|failed
REBASE_STATUS=rebased|already-fresh|conflict|failed|skipped-resume
FORCE_PUSH_STATUS=pushed|noop_same_ref|absent|skipped-repo-unavailable|failed
RESUME_PHASE=force-push-gate
CALLER_KIND=step8b_rebase
STATUS=ok|skipped|conflict|rebase-failed|push-failed|remote-check-failed|changelog-failed|branch-mismatch|postbump-state-corrupt
FINALIZE_SUBCOMMAND=postbump
FINALIZE_WARNINGS=<N>
```

`RESUME_PHASE=force-push-gate` and `CALLER_KIND=step8b_rebase` are present only on `STATUS=conflict`. The resume phase line is informational; the checkpoint file is authoritative. Consumers MUST parse the last `STATUS=` line. The script emits exactly one `STATUS=...` tail record; future debug output must not emit `STATUS=...` lines.

`postmerge` prints one compact Step 14 breadcrumb, optionally one compact Step 15 breadcrumb, then:

```
LOCAL_CLEANUP_STATUS=success|partial|skipped-draft|skipped-merge-false|skipped-bail
VERIFY_MAIN_STATUS=verified|unexpected|skipped
FINALIZE_SUBCOMMAND=postmerge
FINALIZE_WARNINGS=<N>
```

`teardown` prints the tracking issue URL when resolvable, then the final compact Step 18 breadcrumb, then:

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

- `postbump` phase 1 always writes `$IMPLEMENT_TMPDIR/larch-log-batches/version-bump-reasoning.md`. It refreshes the larch-log batch when `ISSUE_NUMBER` is non-empty and `REPO_UNAVAILABLE=false`; `REPO` are forwarded when present. The run ID is resolved from the postbump state file (`read_state RUN_ID`) before falling back to env vars or the tmpdir-basename suffix; this prevents the write going to a wrong-run-ID directory when neither `LARCH_RUN_ID` nor `RUN_ID` is set in the environment. Refresh failures are non-fatal and append to `execution-issues.md`.
- `postbump` phase 2 always runs `check-changelog-present.sh`, then skips when CHANGELOG is absent, fork mode is active, no bump skill is available, `BUMP_TYPE=NONE`, or a non-JSON manifest yields no usable bullets (`CHANGELOG_STATUS=skipped-no-bullets`). When bullets are absent but fallback context is available, it synthesizes `Closed: #<issue>` with an optional `PR_TITLE` suffix and continues. When neither bullets nor tracking-issue fallback context exists, it appends to `execution-issues.md`, emits `CHANGELOG_STATUS=fail-no-manifest-no-issue`, and stops before rebase. Otherwise it inserts or replaces `## [NEW_VERSION] - YYYY-MM-DD` in `CHANGELOG.md`, grouping bullets in Keep-a-Changelog order, then creates a separate `Update CHANGELOG for NEW_VERSION` commit via `commit-changelog.sh`. Changelog read/write/commit failures emit `STATUS=changelog-failed` and stop before rebase.
- `postbump` phase 3 validates the branch and runs `rebase-push.sh --no-push`, adding `--base-remote upstream --base-ref main` in fork mode. Exit 1 writes `$IMPLEMENT_TMPDIR/.postbump-phase` and emits `STATUS=conflict` only for non-fork, repo-available runs; fork and repo-unavailable conflict paths emit `STATUS=rebase-failed`.
- `postbump` phase 4 validates the branch again, skips when `REPO_UNAVAILABLE=true`, otherwise preserves the `check-remote-branch.sh` trichotomy: `present` force-pushes, `absent` leaves initial push to PR creation, and `error` emits `STATUS=remote-check-failed`.
- With `$IMPLEMENT_TMPDIR/.postbump-phase` containing `force-push-gate`, `postbump` skips phases 1-3, runs phase 4 only, and deletes the checkpoint after a successful push/absent/repo-unavailable result.
- Step 14 skips on `DRAFT=true`, then `MERGE!=true`, then a non-empty final-bail-reason file. These skips also force `VERIFY_MAIN_STATUS=skipped`.
- Step 14 cleanup success/partial state comes from `local-cleanup.sh`'s `CLEANUP_SUCCESS`, `CURRENT_BRANCH`, and `BRANCH_DELETED` keys.
- Step 15 runs only after Step 14 actually attempted cleanup. It calls `verify-main.sh --expected-title "$PR_TITLE (#$PR_NUMBER)"`.
- Step 18 first checks `ISSUE_NUMBER` is non-empty and `REPO_UNAVAILABLE=false` before any rename branch. Branch A (`STALL_TRACKING=true`) renames to `stalled` only when `get-issue-info.sh --field state` returns exactly `VALUE=OPEN`; empty `VALUE=` remains a silent skip. Branch B renames to `done` when no merge-path done rename has already applied and either `PR_NUMBER` is set or `DESIGN_ONLY_DONE=true`. Branch C is a no-op.
- Branch A/B renames call `scripts/tracking-issue-write.sh rename` with the `REPO` from the state file when non-empty; otherwise `rename_issue` tries `scripts/resolve-repo.sh` before invoking `rename` without `--repo` (ambient `gh` default). `tracking-issue-write.sh` performs the `gh issue view` / `gh issue edit` calls and fail-closed title redaction.
- On stalled runs (`STALL_TRACKING=true`), Step 18 then probes the repo root with `git rev-parse --show-toplevel`. If `git status --porcelain` is non-empty, it best-effort stashes tracked and untracked edits with a `larch-stalled-<issue>-<step> <utc>` label and records the newest stash ref. Stash failures produce a warning and do not block teardown.
- On stalled runs, Step 18 writes `<git-dir>/larch-stalled-run.txt` atomically with `ISSUE_NUMBER=`, `ISSUE_URL=`, `STALL_STEP=`, `STASH_REF=`, and `TIMESTAMP=`. It resolves `<git-dir>` via `git rev-parse --git-dir` so worktree-style gitdirs are supported. Sentinel write failures produce a warning and do not block teardown.
- Before invoking `kill_session_background_processes` and `cleanup-tmpdir.sh`, teardown finalizes the manifest best-effort, skipped when `RUN_ID` is empty or `REPO_UNAVAILABLE=true`. Before the final status update, teardown probes `$IMPLEMENT_TMPDIR/larch-logs/implement/<RUN_ID>/manifest.json`; when missing, it runs `larch-log.sh init` and immediately tags the synthesized manifest with `status=partial` and `recovery_reason=manifest_lost_mid_run` so a partial run-log directory is identifiable. Manifest finalization on normal paths: when `STALL_TRACKING=true`, sets `stalled_at_step` only (no post-flush `status`/`pr_number` writes on success or design-only teardown). The `larch-log.sh manifest --log-root "$IMPLEMENT_TMPDIR/larch-logs"` call writes the field atomically via temp-and-mv, using `--argjson` for JSON-native values (numbers, booleans, `null`). Teardown does not call `larch-log.sh commit`; committed log flushes are owned by explicit lifecycle flush points.
- Before invoking `cleanup-tmpdir.sh`, teardown writes `$IMPLEMENT_TMPDIR/.run-cleaned-up` best-effort to release the post-/design Stop hook for legitimate end-of-run paths. The write is intentionally before `verify_cleanup_target`, so a refused cleanup still releases the Stop hook; operator cleanup of the leaked tmpdir remains manual. Teardown then runs an execution-issues safety-net flush: if `$IMPLEMENT_TMPDIR/execution-issues.md` is non-empty and its SHA-256 is not already recorded in `.execution-issues-flushed.sha` or the `execution-issues.ndjson` batch (checked via a whole-file `"source_sha256":"<sha>"` grep for backward compat), it appends per-section `execution-issues` NDJSON records (one per `### Category` header, with the actual category name; falls back to one "Tool Failures" record when no headers are present or when jq is absent). For each section the safety-net uses normalized-sha dedup: strip the leading `### Category` header line and leading/trailing blank lines via `normalize_body_for_hash`, compute sha256 of the result, and skip the section when `"source_sha256":"<norm-sha>"` already exists in the batch. This prevents double-emission when whitespace differs between the Step 11 record and the safety-net re-emission of the same content. The `source_sha256` field in each emitted record uses the normalized section sha (falling back to the whole-file sha when normalization fails), before any tmpdir cleanup. The safety net is best-effort and covers failures logged after the normal Step 11 refresh. Teardown then calls `kill_session_background_processes` to kill any background shell processes launched by this session that are still running: it uses `pgrep -f "$IMPLEMENT_TMPDIR"` to find processes that reference the session-unique tmpdir path in their argv, skips the current process ($$), sends SIGTERM, waits 1 second, then SIGKILL to survivors. Best-effort: zero matches are silently skipped; any processes killed emit a warning breadcrumb. The current process ($$) and its direct parent (PPID) are excluded so the orchestrator shell that invoked teardown is not mistakenly terminated. Fixed-string matching via `awk index()` is used instead of regex so dots in the session path cannot overmatch unrelated processes. Session-scoping via the random-suffix tmpdir path minimizes cross-session interference. Teardown then verifies that `basename "$IMPLEMENT_TMPDIR"` starts with `EXPECTED_TMPDIR_BASENAME_PREFIX` and that `$IMPLEMENT_TMPDIR/session-id` matches `EXPECTED_SESSION_ID` when one is present. When both pass, cleanup proceeds. When `EXPECTED_SESSION_ID` is present and the session-id matches but the basename prefix does not, teardown emits `**⚠ 18: cleanup target basename prefix mismatch (expected=<x>, actual=<y>) — session-id match authorizes cleanup. Proceeding.**` and still invokes `cleanup-tmpdir.sh`; this fallback handles stray-underscore or literal-quote prefix bugs (fixed in #1563/#1572) without leaving orphaned tmpdirs. When the session-id doesn't match (or `EXPECTED_SESSION_ID` is absent), teardown appends a best-effort Tool Failures entry to `$IMPLEMENT_TMPDIR/execution-issues.md`, prints `**⚠ 18: cleanup target failed sanity check (basename=<x>, session-id-match=<y/n>) — refusing to rm-rf. Operator must clean manually.**`, skips cleanup, and continues URL printing plus the final breadcrumb. `cleanup-tmpdir.sh` runs after this sanity check, after stalled-run auto-stash/sentinel work, and before the tracking-issue URL print. `teardown` reads all state-file values before cleanup and resolves the issue URL before cleanup so the stalled-run sentinel can carry it.
- Teardown does NOT emit the `Step 18 — done` closing mark. The cap is emitted exclusively by the orchestrator-side terminal Bash block in `skills/implement/SKILL.md` Step 18 AFTER its `--since-last-mark --terse` reports run; a teardown-side mark would race ahead and force those terse reports to slice an empty window starting at `Step 18 — done`. The orchestrator-side cap fixes a token-attribution edge in `scripts/token-report.sh` `vendor_table` (which slices the LAST mark with `$end == null`): without it, vendor records logged after Step 18 in the same JSONL ledger — most plausibly from a subsequent `/implement` run whose launcher falls back to `pwd | sha256_hex` in `token-ledger.sh resolve_session_id()` and writes to the same shared `larch-tokens-<pwd-hash>.jsonl` file — accrue to the prior run's `Step 18 — cleanup` bucket. By the time the orchestrator emits its closing mark, `cleanup-tmpdir.sh` has already removed `$IMPLEMENT_TMPDIR/session-env.sh` and `$IMPLEMENT_TMPDIR/session-id`, so `LARCH_TOKEN_SESSION_ID` resolution falls through to the `pwd-hash` fallback. That landing site is intentional and load-bearing: the cross-run leakage being capped also flows through the same `pwd-hash` fallback, so the cap and the leakage land in the same physical ledger file.

## Invariants

- The state file is never sourced.
- Leaf-script stdout is captured and parsed; leaf-script stderr passes through to the operator.
- All leaf-script failures are best-effort except invocation/state validation. They surface through warning breadcrumbs and tail records, not non-zero exits.
- `--implement-tmpdir` and `--state-file` must be under `/tmp/`, `/private/tmp/`, or the larch cache sessions root.
- post-Step-7a subcommands (`postbump`, `postmerge`, `teardown`) SHOULD prefer direct `append-tool-failure.sh`/`larch-log.sh append` safety-net paths over adding prompt prose. `teardown` is allowed to append cleanup-sanity failures to `$IMPLEMENT_TMPDIR/execution-issues.md` because it immediately follows with the safety-net flush before tmpdir deletion. `postbump` MAY append warnings to `$IMPLEMENT_TMPDIR/execution-issues.md`; shared external-implementer / pre-push flush paths append that unflushed tail before the next log commit when available, and teardown remains the fallback.
- The literal phase identifier `force-push-gate`, the contents of `$IMPLEMENT_TMPDIR/.postbump-phase`, is reproduced byte-identically in `skills/implement/SKILL.md` Step 8 conflict-resume prose. Changes to the recognized-phase enum here require a paired SKILL.md update.
- The orchestrator MUST parse the last `STATUS=` line in `postbump` stdout. The script emits exactly one `STATUS=...` line as part of the trailing tail records; future debug output is not permitted to emit `STATUS=...` lines.

## Primary Callers

- `skills/implement/SKILL.md` Step 8 writes the postbump state file and invokes `postbump`.
- `skills/implement/SKILL.md` Step 14 entry writes the state file and invokes `postmerge`.
- `skills/implement/SKILL.md` Step 18 invokes `teardown`.

## Test Harness

`scripts/test-implement-finalize.sh` is the offline regression harness. It copies this script into a `/tmp` sandbox with stub sibling helpers and git/gh shims, exercises the subcommands, postbump changelog/category/checkpoint/error paths, stalled-run stash/sentinel handling, `.run-cleaned-up` Stop-hook release behavior before cleanup validation, and state-file parsing, normalizes elapsed-time parentheticals, and is wired through `make test-implement-finalize`. `scripts/test-restore-finalize-state.sh` covers the pre-teardown state restoration helper. `scripts/test-finalize-sanity-check.sh` covers the Step 18 cleanup target sanity check specifically.

## Edit In Sync

When changing this script or its state-file inputs, update this contract, `scripts/commit-changelog.md`, `scripts/lib-execution-issues.sh`, `skills/implement/scripts/flush-execution-issues.sh`, `skills/implement/SKILL.md` Steps 8, 8a, 8b, and 14-18, `scripts/test-implement-finalize.sh`, `scripts/test-implement-finalize.md`, `scripts/restore-finalize-state.md`, `.claude/skills/bump-version/SKILL.md`, `skills/implement/references/rebase-rebump-subprocedure.md`, `SECURITY.md`, `Makefile`, and the harness table in `docs/linting.md` if the public target or coverage changes.
