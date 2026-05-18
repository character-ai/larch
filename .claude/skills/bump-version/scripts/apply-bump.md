# apply-bump.sh

Applies a computed semver bump to `.claude-plugin/plugin.json` and creates the single version-only bump commit used by `/implement` Step 8 and the Rebase + Re-bump Sub-procedure.

## Purpose

`apply-bump.sh --new-version X.Y.Z` is the mutation half of the dev-only `/bump-version` skill. It assumes `classify-bump.sh` has already selected `NEW_VERSION`; this script validates the repo state, rewrites the plugin version, checks the current `origin/main` version to avoid same-version duplicate bump commits and version-regression bumps (`NEW_VERSION < ORIGIN_VERSION`), and commits `Bump version to X.Y.Z`.

## Output Contract

On success:

```text
APPLIED=true
COMMIT_SHA=<sha>
```

On failure:

```text
APPLIED=false
ERROR=<message>
```

The script exits 0 only when the bump commit was created. It exits 1 for invalid arguments, dirty worktree, JSON validation/rewrite failures, origin/main version-guard failures (same-version race detection and `NEW_VERSION < ORIGIN_VERSION` regression guard), and commit failure.

## Invariants

- The working tree must be clean before any mutation. `git status --porcelain` covers staged, unstaged, and untracked files.
- Dirty-worktree failures include `/implement` phantom-file guidance:
  `Mid-/implement run: check tracking issue Execution Issues section or \$IMPLEMENT_TMPDIR/execution-issues.md for phantom file warnings.` The
  `\$IMPLEMENT_TMPDIR` token is intentionally backslash-escaped in the script
  string so manual invocations under `set -u` do not expand an unset
  `IMPLEMENT_TMPDIR`.
- `.claude-plugin/plugin.json` must parse as JSON before rewrite.
- The rewrite is atomic: `jq` writes to a temp file, then `mv` replaces `plugin.json`.
- The pre-commit version probes run after `git add` and before `git commit`: fetch `origin main`, read `origin/main:.claude-plugin/plugin.json`, require strict `^[0-9]+\.[0-9]+\.[0-9]+$`; fail closed if the origin version equals `NEW_VERSION` (same-version race); also fail closed if `NEW_VERSION < ORIGIN_VERSION` (regression guard — catches cases where a rebase conflict was resolved to the branch's stale version rather than main's).
- Every pre-commit probe failure rolls back by restoring from `$BACKUP` and unstaging `plugin.json` with `git reset HEAD "$PLUGIN_JSON"`.
- No `larch-log-flush.sh` tail-call after the bump commit: the rebase+re-bump machinery (`drop-bump-commit.sh`) requires the bump commit to remain at HEAD.
- Commit failure uses the existing post-commit rollback path: restore from `$BACKUP`, unstage `plugin.json`, and emit `ERROR=git commit failed; rolled back ...`.
- The backup file is consumed on success or rollback; it must not remain after a normal script exit.

## Makefile Wiring

The regression harness is:

```makefile
test-apply-bump:
    bash scripts/test-apply-bump.sh
```

`test-apply-bump` is listed in `.PHONY` and in exactly one `test-harnesses-N` shard so `make lint` runs it through the `lint: test-harnesses lint-only` chain.

## Test Harness

`scripts/test-apply-bump.sh` creates temporary repos and PATH-stubs selected `git fetch` / `git show` calls while delegating normal git operations to the real binary. It covers success, fetch failure rollback, same-version rollback, differing-origin success, malformed-origin rollback, dirty worktree rejection including the phantom-file guidance text, commit-failure rollback, and regression-guard rollback (NEW_VERSION < ORIGIN_VERSION).

## Edit-in-sync Rules

Update this file with any behavioral change to `.claude/skills/bump-version/scripts/apply-bump.sh`. In the same PR, keep these files synchronized:

- `.claude/skills/bump-version/SKILL.md` "How it works" section.
- `skills/implement/SKILL.md` Step 8 handling for `/bump-version` failures.
- `skills/implement/references/rebase-rebump-subprocedure.md` when caller-kind routing changes.
- `scripts/test-apply-bump.sh` and `scripts/test-apply-bump.md`.
