## Goal
Fix 5 ship-pr.sh helper polish issues: apply-bump rebase state, git-push stderr dedup, drop-bump-commit walk-back, create-pr empty error, step-8a changelog fallback

## Implementation Plan

Five targeted fixes to the ship-pr.sh subprocess tree. Each fix is
self-contained; all land in a single PR.

### Item E — apply-bump.sh: detect rebase-in-progress before dirty-tree check

**Target**: `.claude/skills/bump-version/scripts/apply-bump.sh`

Before the existing `_raw_status` dirty-tree check, add a new block that
runs `git status --porcelain` and greps for lines beginning with unmerged-path
status codes (`UU `, `AA `, `DD `, `AU `, `UA `, `DU `, `UD `). If any exist:
- Collect the affected file paths.
- Emit `APPLIED=false ERROR="rebase in progress with unmerged paths: <files>. Resolve conflicts (git rebase --continue or git rebase --abort) before bumping."`
- Exit with code **4** (distinct from the existing exit-1 dirty-tree path).

`ship-pr.sh::run_rebase_rebump()` already routes all non-zero exits from
`apply-bump.sh` to `exit_stall` without a phantom-file workaround; no
change needed there. Update `apply-bump.md` exit-code table and test harness.

**Test**: In `scripts/test-apply-bump.sh`, add sub-test that creates a git
repo, stages a conflict by simulating a `UU` unmerged-path fixture (write
a blob to `.git/MERGE_HEAD`, stage both sides via `git update-index --cacheinfo`
so `git status --porcelain` shows `UU`), run `apply-bump.sh`, assert exit 4
and error substring `rebase in progress`.

### Item F — git-push.sh: stderr deduplication across retry attempts

**Target**: `scripts/git-push.sh`

In the retry loop, capture each `git push` stderr into a per-attempt temp
file. After all attempts, deduplicate identical consecutive stderr blocks
before emitting on failure. If the same block repeated M times, emit it
once followed by a line `(repeated M times)`. Update `git-push.md`.

**Test**: In `scripts/test-git-push.sh`, add a stub `git push` that emits
a fixed stderr line (simulating a non-fast-forward rejection) on all 3
attempts; assert the combined captured failure stderr contains the line
exactly once and includes `(repeated 3 times)`.

### Item H — drop-bump-commit.sh: walk back up to --max-depth commits

**Target**: `scripts/drop-bump-commit.sh`

Add optional `--max-depth N` flag (default 10). Change Guard 2 from a
HEAD-only subject check to a walk: iterate from depth 0 to (max_depth-1),
checking each `HEAD~D` subject against the bump pattern. Record the first
match depth `found_at`.

- If `found_at == 0`: use existing `git reset --hard HEAD~1` (no change to
  current behavior for the common case).
- If `found_at > 0`: drop via `git rebase --onto HEAD~(found_at+1) HEAD~found_at`
  (replays commits above the bump commit on top of the commit before it).
- If no bump found within max_depth: emit `DROPPED=false` with warning
  naming the walked depth.

Guards 3 and 4 are applied to the found commit (not necessarily HEAD). Guard 4
file check is `git diff --name-only HEAD~(found_at+1) HEAD~found_at`.
Update `drop-bump-commit.md`.

**Tests in `scripts/test-drop-bump-commit.sh`**:
- Fixture: HEAD = larch-log-flush commit, HEAD~1 = bump commit. Assert
  `DROPPED=true` and the flush commit preserved as new HEAD.
- Fixture: bump commit at depth > max_depth (--max-depth 2, bump at HEAD~3).
  Assert `DROPPED=false` with warning mentioning walked depth.

### Item I — create-pr.sh: never produce empty error block on failure

**Target**: `scripts/create-pr.sh`

The existing `gh pr create` failure path at line ~178 emits only the captured
`PR_STDERR` but does not guarantee non-empty output. Fix:

1. Always capture both stdout and stderr of `gh pr create` to separate tmps.
2. On non-zero exit, compose a diagnostic block:
   - argv used (redacted via `redact-tmpdir-paths.sh`).
   - captured stderr (already captured in `PR_STDERR_FILE`).
   - exit code.
   - last 10 lines of captured stdout.
3. If all of the above are empty: emit the stub
   `(no diagnostic captured; gh pr create exited <N> with no output. Manual investigation required.)`.
4. Emit to stderr via `larch_err` and exit 2.

Update `create-pr.md`.

**Test**: Add case to `scripts/test-create-pr.sh` where the `gh` stub exits 1
with empty stderr on `pr create`; assert the resulting stderr of `create-pr.sh`
contains at least the argv string (not an empty backtick block).

### Item J — implement-finalize.sh: changelog fallback bullet when no manifest

**Target**: `scripts/implement-finalize.sh` → `maybe_update_changelog()` →
the `changelog_categories_to_markdown` failure branch (lines ~694-703).

Change the silent-skip branch to:
1. Call `read_state ISSUE_NUMBER` and `read_state PR_TITLE`.
2. If `ISSUE_NUMBER` is non-empty: write a fallback `categories_md` containing
   `### Changed\n\n- Closed: #<N><optional " — <PR_TITLE>">` and continue with
   `write_changelog_entry` normally.
3. If `ISSUE_NUMBER` is empty: emit `CHANGELOG_STATUS=fail-no-manifest-no-issue`,
   append execution issue with text including
   `ERROR=Cannot generate changelog bullet: no manifest AND no tracking-issue context.`,
   emit warn line, and return 1 (fail, not skip).

Update `implement-finalize.md` CHANGELOG_STATUS enum.

**Test**: Create `skills/implement/scripts/test-step-8a-changelog.sh` that
exercises `maybe_update_changelog` via a stub `implement-finalize.sh` shim:
- Fixture (a): valid manifest with `summary_bullets_categorized` → runs to
  completion (CHANGELOG_STATUS=updated or verifiable side-effect).
- Fixture (b): empty manifest + ISSUE_NUMBER + PR_TITLE set → fallback bullet
  `Closed: #N` appears in CHANGELOG.md.
- Fixture (c): empty manifest + ISSUE_NUMBER unset → `CHANGELOG_STATUS=fail-no-manifest-no-issue`.

Update `implement-finalize.md` and add harness entry to Makefile / linting.

### Edge cases and invariants preserved

- Bash 3.2 compat: use `while IFS= read -r` loops, `case`/pattern matching,
  no associative arrays, no `mapfile`.
- apply-bump.sh: unmerged-path check runs BEFORE the dirty-tree check so it
  never reaches the `_non_internal` filter.
- drop-bump-commit.sh: for found_at=0 case the existing `git reset --hard HEAD~1`
  is preserved exactly (same observable behavior, faster).
- create-pr.sh: the `PR_STDERR_FILE` tmpfile is already set up; we add a
  parallel `PR_STDOUT_FILE` tmp for the PR creation stdout capture.
- implement-finalize.sh: when falling back to a synthetic bullet, `postbump_mark`
  still runs at the correct point (it's called after `changelog_categories_to_markdown`,
  now after the fallback branch too).

## Test plan
(no test plan section in plan-file)
