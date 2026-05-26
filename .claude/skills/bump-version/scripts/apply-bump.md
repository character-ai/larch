# apply-bump.sh

Applies a computed semver bump to `.claude-plugin/plugin.json` and creates the single version-only bump commit used by `/implement` Step 8 and the Rebase + Re-bump Sub-procedure.

## Purpose

`apply-bump.sh --new-version X.Y.Z` is the mutation half of the dev-only `/bump-version` skill. It assumes `classify-bump.sh` has already selected `NEW_VERSION`; this script validates the repo state, rewrites the plugin version, checks the current `origin/main` version, and commits `Bump version to X.Y.Z`. When `origin/main` has advanced to the same or a higher version (parallel-clone bump race), the script silently re-classifies and retries up to 10 times before bailing loudly.

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

The script exits 0 only when the bump commit was created. It exits 1 for invalid arguments, dirty worktree, JSON validation/rewrite failures, commit failure, or exhaustion of the 10-retry collision cap. It exits 4 when unmerged paths from an in-progress merge or rebase are detected (checked before the general dirty-tree guard so callers can distinguish that shape from a generic dirty worktree). A same-version or version-regression collision no longer exits 1 on the first attempt; the script retries up to 10 times instead.

## Invariants

- Before any mutation, the working tree is verified in two sequential checks: (1) unmerged-path pre-check (`UU`, `AA`, `DD`, `AU`, `UA`, `DU`, `UD` porcelain codes) exits 4 immediately with an in-progress merge-or-rebase error; (2) general dirty-tree check allows only larch-internal untracked artifacts (`*.launcher-stderr` review-dispatch sidecars, `*.redacted.log` relevant-checks output) and fails with exit 1 on anything else.
- Dirty-worktree failures include `/implement` phantom-file guidance:
  `Mid-/implement run: check tracking issue Execution Issues section or \$IMPLEMENT_TMPDIR/execution-issues.md for phantom file warnings.` The
  `\$IMPLEMENT_TMPDIR` token is intentionally backslash-escaped in the script
  string so manual invocations under `set -u` do not expand an unset
  `IMPLEMENT_TMPDIR`.
- `.claude-plugin/plugin.json` must parse as JSON before rewrite.
- The rewrite is atomic: `jq` writes to a temp file, then `mv` replaces `plugin.json`.
- The pre-commit version probes run inside a retry loop (cap 10): fetch `origin main`, read `origin/main:.claude-plugin/plugin.json`, require strict `^[0-9]+\.[0-9]+\.[0-9]+$`. On a same-version or regression collision (`NEW_VERSION == ORIGIN_VERSION` or `NEW_VERSION < ORIGIN_VERSION`), the script rolls back, re-classifies the bump type from the original (current, initial-target) pair, computes a new `NEW_VERSION` relative to `ORIGIN_VERSION`, emits one breadcrumb via `emit_breadcrumb --category=retry`, and retries. After 10 failed retries the script bails with `APPLIED=false ERROR=origin/main bump race: could not land version after 10 retries ...`. A fetch failure or malformed origin version still fails immediately (no retry on those paths).
- Every pre-commit probe failure rolls back by restoring from `$BACKUP` and unstaging `plugin.json` with `git reset HEAD "$PLUGIN_JSON"`.
- On each retry a breadcrumb is emitted via `emit_breadcrumb --category=retry`: `apply-bump: retry N/10 origin/main=X.Y.Z new-version=X.Y.Z`. This is **not** the same stream as `emit` / `emit_kv`: contract key/value lines always go to the caller-visible stream (FD 3 after `larch_quiet_init` in `scripts/lib-quiet.sh`, or ordinary stdout when quiet mode is inactive). `emit_breadcrumb` writes to the **quiet log** by default when quiet init is active; set `LARCH_QUIET_BREADCRUMBS=1` to surface breadcrumbs on the caller-visible stream (or `LARCH_QUIET_BREADCRUMB_FD` to a numeric inherited FD for nested routing—see `scripts/lib-quiet.md`). Offline harnesses that assert machine-readable stdout often export `LARCH_QUIET_DISABLE=1` (e.g. `scripts/test-apply-bump.sh`), which skips quiet redirection so breadcrumbs and contract lines share real stdout; operators capturing only FD 3 in a quiet-active session will **not** see default-routing breadcrumbs.
- No `larch-log-flush.sh` tail-call after the bump commit: the rebase+re-bump machinery (`drop-bump-commit.sh`) walks back from HEAD and drops the most recent matching bump commit, so no post-bump flush commit is needed here.
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

`scripts/test-apply-bump.sh` creates temporary repos and PATH-stubs selected `git fetch` / `git show` calls while delegating normal git operations to the real binary. It covers first-attempt success, fetch failure rollback, same-version and regression collisions with re-classify retries (including breadcrumb assertions), differing-origin success, malformed-origin rollback, dirty worktree rejection (phantom-file guidance), unmerged-path exit-4 handling, commit-failure rollback, internal-artifact tolerance, and sequence-driven fixtures for multi-collision, cap-exhaustion, no-collision baseline, and exact breadcrumb shape (sub-tests K–O).

## Edit-in-sync Rules

Update this file with any behavioral change to `.claude/skills/bump-version/scripts/apply-bump.sh`. In the same PR, keep these files synchronized:

- `.claude/skills/bump-version/SKILL.md` "How it works" section.
- `skills/implement/SKILL.md` Step 8 handling for `/bump-version` failures.
- `skills/implement/references/rebase-rebump-subprocedure.md` when caller-kind routing changes.
- `scripts/test-apply-bump.sh` and `scripts/test-apply-bump.md`.
