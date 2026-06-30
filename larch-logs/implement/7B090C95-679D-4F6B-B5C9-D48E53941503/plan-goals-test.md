## Goal
Implement issue #5863: [IMPLEMENTING] [BUG] recovery-paths NUL pathspec drops git-mv source path, leaving staged deletion uncommitted and causing dirty-tree stall before push.

## Implementation Plan
## Summary

`_parse_porcelain_z` in `dispatch_helpers.py` parses git rename (`R`) entries from `git status --porcelain=v1 -z` output but silently discards the old path (the rename source). As a result, `compute_recovery_paths` never includes the source path in the NUL pathspec written to `implementation-commit-paths.nul`. When Step 4 commits via `git commit --only --pathspec-from-file`, the old path is absent from the pathspec, so git's `--only` mode leaves it untouched in HEAD. The staged deletion created by `git mv` remains in the real index uncommitted. The ship driver's `assert_clean_worktree` then detects these staged deletions before push and raises `ShipError("uncommitted working-tree changes detected before push")`, causing a stall (exit 4, `outcome=STALLED`).

## Original report

<!-- &#8203;larch: intentional neutralization of larch marker to prevent downstream parsing -->

`recovery-paths` NUL pathspec omits staged index deletions from `git mv`/`git rm` on the main-agent path, causing a dirty-tree stall before push.

Root cause: `recovery-paths` diffs working-tree porcelain (postlaunch vs prelaunch), but `git mv` stages the old-path deletion in the index without leaving the old file in the working tree — so `git add` cannot restage it and it is excluded from the NUL pathspec. Step 4 commit only includes new paths, leaving staged deletions uncommitted. Ship driver pre-push clean-tree guard detects the uncommitted staged deletions and stalls with "uncommitted working-tree changes detected before push".

Fix suggestion: in `recovery-paths`, additionally collect paths that are staged in the index as deleted (`D` in column X of `git status --porcelain`) but absent from the working tree, and include them in the NUL pathspec so `git commit --pathspec-from-file` can include them. Alternatively use `git diff --cached --name-only --diff-filter=D` as a supplemental source.

## Reproduction scenario

1. Open a GitHub issue with no `larch:plan` block.
2. Run `/implement --force --merge <issue-N>` (or `/im -f <issue-N>`) — forces `coder=claude`.
3. In Step 2.4 (main-agent implementation), use `git mv old-path new-path` to relocate one or more files, then use the `Edit` tool to modify the destination file.
4. `recovery-paths --capture-postlaunch` runs after edits; `implementation-commit-paths.nul` is written.
5. Step 3 `checks-commit-route` commits using `git commit --only --pathspec-from-file implementation-commit-paths.nul --pathspec-file-nul`.
6. The commit includes the new path but not the deletion of the old path.
7. Step 8+ ship driver runs `assert_clean_worktree` before push; sees staged deletions; raises `ShipError`; exits with code 4 (`outcome=STALLED`).
8. Stall recovery classifies as `transient-infra / step8-shippr`.
9. Operator must manually commit the staged deletions, then reship.

The workaround applied in the observed run: `git commit -m "Remove old paths (moved to scripts/)"` to commit the staged deletions, followed by a reship which succeeded.

## Expected behavior

`compute_recovery_paths` includes the source path of any `git mv` rename in the NUL pathspec so that `git commit --only` stages the working-tree deletion of the old path and commits it alongside the new path. The branch stays clean; `assert_clean_worktree` passes; the ship driver pushes successfully on the first attempt.

## Observed behavior

After a `git mv` in Step 2.4:

- `implementation-commit-paths.nul` contains only the new (destination) path.
- The Step 4 commit adds the destination file but leaves the source file in HEAD unchanged.
- The real index retains the staged deletion (`D ` status) from `git mv`.
- `git status --short` shows `D  <old-path>` entries on the feature branch.
- `python/larch/git/push.py` `assert_clean_worktree` detects this and raises `ShipError("uncommitted working-tree changes detected before push")`.
- `/implement` exits with code 4 / `outcome=STALLED`.

## Root cause analysis

**Confident — confirmed from source and test.**

`git status --porcelain=v1 -z` encodes a staged rename as two NUL-separated records: `R  new-path\0old-path`. `_parse_porcelain_z` (dispatch_helpers.py:131–148) correctly skips the second NUL record for `R`/`C` entries to avoid misinterpreting it as a new status entry, but it discards the skipped value entirely:

```python
# dispatch_helpers.py:144-145
if ("R" in status or "C" in status) and idx < len(items):
    idx += 1  # skips items[idx] — the old path — without recording it
tuples.add((status, rel))   # only the new path (rel) is recorded
paths.add(rel)
```

Because `old-path` is never added to `tuples` or `paths`, `_collect_recovery_candidates` never emits it into the NUL pathspec. `git commit --only --pathspec-from-file` therefore does not stage the working-tree deletion of the old path into the temporary index it constructs from HEAD. The old file survives in the commit untouched. The staged deletion is orphaned in the real index.

The existing test at `test_implement_dispatch.py:1419` documents this as intentional behavior — it asserts `["RENAMED.md"]` (destination only) — but the behavior is incorrect: the source path's deletion must also be committed.

## Evidence

- **`python/larch/implement/dispatch_helpers.py:131–148`** — `_parse_porcelain_z`: consumes `items[idx]` for `R`/`C` entries via `idx += 1` without recording `old_rel`.
- **`python/larch/implement/dispatch_recovery.py:87–118`** — `_collect_recovery_candidates` / `compute_recovery_paths`: iterates only `post.tuples`; old paths absent from `post.tuples` are never candidates.
- **`python/larch/git/push.py:34–42`** — `assert_clean_worktree`: runs `git status --porcelain` before every push; any non-empty output raises `ShipError`.
- **`python/tests/implement/test_implement_dispatch.py:1399–1419`** — `test_step2_dispatch_rename_recovery_uses_destination_path`: asserts `["RENAMED.md"]` after `git mv README.md RENAMED.md`; documents (and pins) the incomplete behavior.
- **Observed run**: feature branch `sergey-zhupanov/implementing-migrate-claude-scripts-admi-496`, run ID `00AD226A-2DBD-40C8-BB25-E68C82C8695A`, PR #497 on `character-tech/dev-tools`. After Step 4 commit (sha `42b9b21`), `git status --short` showed five `D ` entries for moved `.claude/scripts/admin-add-user*` files. Workaround: manual `git commit` of staged deletions followed by reship.

## Affected files

- `python/larch/implement/dispatch_helpers.py` — `_parse_porcelain_z` (line 131): fix site; must record `old_rel` when skipping the rename source.
- `python/larch/implement/dispatch_recovery.py` — `_collect_recovery_candidates` / `compute_recovery_paths`: secondary fix site if the fix is applied here instead.
- `python/tests/implement/test_implement_dispatch.py` — `test_step2_dispatch_rename_recovery_uses_destination_path` (line 1399): must be updated to assert `["README.md", "RENAMED.md"]` (both paths, sorted) after the fix; also add a new integration test covering `git commit --only` leaves no staged deletions.

## Suggested fix(es)

**Option A (preferred — minimal, correct layer):** Record the rename source in `_parse_porcelain_z` alongside the destination:

```python
# dispatch_helpers.py — _parse_porcelain_z, lines 144-145
if ("R" in status or "C" in status) and idx < len(items):
    old_item = items[idx]
    idx += 1
    if old_item:
        old_rel = old_item.decode("utf-8", "surrogateescape")
        tuples.add(("D ", old_rel))   # synthetic deletion entry for source
        paths.add(old_rel)
tuples.add((status, rel))
paths.add(rel)
```

This ensures `_collect_recovery_candidates` emits the old path into the NUL pathspec. `git commit --only` then stages its working-tree state (deleted) from the temporary HEAD index, committing the deletion.

**Option B (defense-in-depth supplement):** After collecting candidates from porcelain diff in `compute_recovery_paths`, add a supplemental pass that captures staged index deletions missing from the working tree via `git diff --cached --name-only --diff-filter=D`. Merge with candidates before writing the NUL file. This handles `git rm` cases too (which would also produce staged deletions not visible in working-tree porcelain diffs, though `git rm` on tracked files does appear in porcelain with `D ` status and would already be caught by Option A if `_parse_porcelain_z` correctly includes them).

**Test update required for either option:**
- Update `test_step2_dispatch_rename_recovery_uses_destination_path` to assert both old and new paths are present.
- Add a test that performs `git mv`, captures recovery paths, runs `git commit --only --pathspec-from-file`, and asserts `git status --porcelain` is empty afterward.

## Open questions

- Does `git rm` (without `git mv`) produce a `D ` entry in `git status --porcelain=v1 -z`? If so, it would already appear in `post.tuples` and be captured correctly — only the `R`-entry skip path is broken. Confirm before writing Option B test cases.
- Should `_parse_porcelain_z` record the old path with `("D ", old_rel)` synthetic status, or with the original `R ` status of the rename entry? Using `"D "` is semantically cleaner since the old path IS being deleted; using `R ` might confuse downstream consumers that key on exact status strings.
- The test at line 1399 uses `coder=codex` (external implementer recovery path), not `coder=claude` (main-agent path). Verify whether the same `_parse_porcelain_z` is used on both paths, or whether the main-agent path has a separate porcelain capture that is also affected.

## Test plan
(no test plan section in plan-file)
