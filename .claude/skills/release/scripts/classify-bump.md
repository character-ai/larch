# classify-bump.sh

`classify-bump.sh` is the deterministic classifier for the dev-only `/release` skill. It inspects the public plugin surface (`skills/**`, `agents/**`), writes `$IMPLEMENT_TMPDIR/bump-version-reasoning.md` when the session tmpdir is writable (otherwise a `mktemp`-created `bump-version-reasoning.XXXXXX` under `${TMPDIR:-/tmp}`), and emits `CURRENT_VERSION`, `NEW_VERSION`, `BUMP_TYPE`, and `REASONING_FILE`.

## Optional `--base <ref>` and `--head <ref>`

When `--base` is set (consumer: dev-only `/release` via `release-prepare.sh`):

- Resolves `<ref>` with `git rev-parse --verify` and uses that commit as `BASE` directly (skips merge-base resolution and the best-effort `git fetch origin main`).
- Skips the idempotency short-circuit (`BUMP_TYPE=NONE` for trailing `Bump version to X.Y.Z` commits), so aggregate classification over `BASE..HEAD` is not suppressed by historical version commits on `main`. `/release` consumers never see `NONE` from this script.

When `--head <ref>` is set (consumer: dev-only `/release` via `release-prepare.sh`):

- Resolves `<ref>` with `git rev-parse --verify` and uses that commit as the diff head instead of `HEAD`, so aggregate classification is anchored to `origin/main` (or another explicit ref) when the caller is not checked out at the release tip.
- Reads `CURRENT_VERSION` from `git show <ref>:.claude-plugin/plugin.json` and fails closed when the worktree `plugin.json` version disagrees.

When `--base` / `--head` are omitted, the classifier uses the merge-base against `main` / `origin/main` and applies the local idempotency shortcut.

## Idempotency

The classifier treats the branch as already versioned when the idempotency head is a `Bump version to X.Y.Z` commit. Before checking that subject, it walks past up to three transparent `Update CHANGELOG for ...` commits that touch only `CHANGELOG.md` or `chore(larch-logs): ...` commits that touch only `larch-logs/**`. Subject matches alone are not trusted.

## Edit-in-sync

Keep this file aligned with `.claude/skills/release/scripts/classify-bump.sh`, `.claude/skills/release/scripts/test-classify-bump.sh`, and `.claude/skills/release/scripts/release-prepare.sh`.
