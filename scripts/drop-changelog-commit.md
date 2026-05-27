# drop-changelog-commit.sh

**Purpose**: Drop the most recent `Update CHANGELOG for X.Y.Z` commit (for an exact version) found within the last `--max-depth` commits (default 20). Narrow primitive paired with `scripts/drop-bump-commit.sh` and used by `/implement`'s Rebase + Re-bump Sub-procedure to strip the stale `Update CHANGELOG` commit that accompanies a dropped bump commit. Without this drop, the stale commit is replayed on the next rebase and conflicts with `origin/main` once main has its own `## [X.Y.Z]` section (issue #2952 Bug A).

**Invariant**: This primitive only ever drops a commit whose subject is the exact literal `Update CHANGELOG for $version` AND whose diff touches exactly `CHANGELOG.md`. Anything else is a no-op with `DROPPED=false`. The caller passes the version it just learned from `drop-bump-commit.sh`'s `OLD_BUMP_SHA`, so the bump-and-changelog pair is always dropped as a unit.

## Guards (all must pass for `DROPPED=true`)

1. **Clean worktree (tracked files)** — `git status --porcelain --untracked-files=no` must be empty. Untracked files are excluded because the drop operation does not affect them.
2. **Matching commit found within depth** — walk `HEAD`, `HEAD~1`, … up to `--max-depth` commits; the first commit whose subject equals `Update CHANGELOG for $version` is selected. If none found, `DROPPED=false` with a warning naming the walked depth.
3. **Parent of found commit exists** — `HEAD~(found_at+1)` must resolve.
4. **Touches exactly CHANGELOG.md** — `git diff --name-only HEAD~(found_at+1) HEAD~found_at` must equal `CHANGELOG.md`. Any extra path refuses the drop.

## Flags

- **`--version X.Y.Z`** (required): exact version string to match in the subject. Must satisfy `^[0-9]+\.[0-9]+\.[0-9]+$`.
- **`--max-depth N`** (default 20): walk at most N commits back from `HEAD`.

## Output contract

- `DROPPED=true|false` (stdout, KEY=VALUE)
- `OLD_CHANGELOG_SHA=<sha>` (stdout, only when `DROPPED=true`)
- `WARN: ...` lines on stderr explain which guard refused the drop

## Drop mechanism

- When the changelog commit is at HEAD (`found_at=0`): `git reset --hard HEAD~1`.
- When the changelog commit is deeper (`found_at>0`): `git rebase --onto HEAD~(found_at+1) HEAD~found_at` — replays the commits above the changelog commit onto its parent, effectively removing the changelog commit from history.

## Exit codes

- `0` — success, including no-op cases (inspect `DROPPED`)
- `1` — git error during the drop (reset or rebase); rebase is aborted automatically before exit

## Test harness

`scripts/test-drop-changelog-commit.sh` — offline regression harness wired into `make test-harnesses` (Makefile target `test-drop-changelog-commit`). Creates isolated temp repos with controlled commit shapes.

## Edit-in-sync

When editing `scripts/drop-changelog-commit.sh`:
- Update this file (`scripts/drop-changelog-commit.md`) for any behavioral change.
- Update `scripts/test-drop-changelog-commit.sh` for any guard logic change.
- Update `scripts/drop-bump-commit.md` cross-reference if the pairing contract changes.
- Update `scripts/ship-pr.md` if the caller surface changes.
