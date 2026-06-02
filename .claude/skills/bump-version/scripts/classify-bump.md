# classify-bump.sh

`classify-bump.sh` is the deterministic classifier for the dev-only `/bump-version` skill. It inspects the public plugin surface (`skills/**`, `agents/**`), writes the reasoning file, and emits `CURRENT_VERSION`, `NEW_VERSION`, `BUMP_TYPE`, and `REASONING_FILE`.

## Optional `--base <ref>` and `--head <ref>`

When `--base` is set (consumer: dev-only `/release` via `release-prepare.sh`):

- Resolves `<ref>` with `git rev-parse --verify` and uses that commit as `BASE` directly (skips merge-base resolution and the best-effort `git fetch origin main`).
- Skips the per-PR idempotency short-circuit (`BUMP_TYPE=NONE` for trailing `Bump version to X.Y.Z` commits), so aggregate classification over `BASE..HEAD` is not suppressed by per-PR bump commits on `main`.

When `--head <ref>` is set (consumer: dev-only `/release` via `release-prepare.sh`):

- Resolves `<ref>` with `git rev-parse --verify` and uses that commit as the diff head instead of `HEAD`, so aggregate classification is anchored to `origin/main` (or another explicit ref) when the caller is not checked out at the release tip.

When `--base` / `--head` are omitted, behavior is unchanged from the default `/bump-version` / `/implement` path.

## Idempotency

The classifier treats the branch as already bumped when the idempotency head is a `Bump version to X.Y.Z` commit. Before checking that subject, it walks past up to three transparent commits from the bump pipeline: `Update CHANGELOG for X.Y.Z` commits that touch only `CHANGELOG.md`, and `chore(larch-logs): ...` commits that touch only `larch-logs/**`. Subject matches alone are not trusted.

## Edit-in-sync

Keep this file aligned with `.claude/skills/bump-version/SKILL.md`, `.claude/skills/bump-version/scripts/apply-bump.md`, `scripts/commit-changelog.md`, and `scripts/drop-bump-commit.md` when the bump/changelog commit shape changes.
