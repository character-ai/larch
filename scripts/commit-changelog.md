# commit-changelog.sh

**Purpose**: Commit a `CHANGELOG.md` update as a separate commit with subject `Update CHANGELOG for <version>`. This keeps the version bump commit limited to configured bump files while preserving a stable CHANGELOG audit commit.

## Contract

- Requires `--version X.Y.Z`; accepts optional `--replaces-version X.Y.Z`.
- The commit subject MUST NOT match `^Bump version to [0-9]+\.[0-9]+\.[0-9]+$`.
- The tracked worktree may be clean or dirty only for `CHANGELOG.md`; untracked files are ignored.
- If `--replaces-version` is present, the helper rewrites the matching old version heading to the new version before committing. If the old heading is absent, it emits `COMMITTED=false` and exits 0.
- If `CHANGELOG.md` has no staged or unstaged delta, it emits `COMMITTED=false` and exits 0.
- Commits are created through `scripts/git-commit.sh -m "Update CHANGELOG for <version>" --only CHANGELOG.md`.

## Output

- `COMMITTED=true|false`
- `COMMIT_SHA=<sha>` when a commit is created
- `ERROR=<text>` on errors and selected no-op diagnostics

## Primary Callers

- `scripts/implement-finalize.sh` Step 8a after it writes the CHANGELOG entry.
- `scripts/ship-pr.sh` rebase + re-bump paths after `apply-bump.sh`.
- `skills/implement/references/rebase-rebump-subprocedure.md` step 4a for prompt-side re-bump recovery.

## Test Harness

`scripts/test-commit-changelog.sh`, wired through Makefile target `test-commit-changelog`.

## Edit-in-sync

When editing `scripts/commit-changelog.sh`:
- Update this file.
- Update `scripts/implement-finalize.md` for Step 8a commit semantics.
- Update `scripts/drop-bump-commit.md` if the commit subject or bump/drop interaction changes.
- Update `scripts/ship-pr.md` and `skills/implement/references/rebase-rebump-subprocedure.md` for rebase + re-bump behavior changes.
- Update `skills/implement/references/conflict-resolution.md` if replaying CHANGELOG commits changes conflict handling.
