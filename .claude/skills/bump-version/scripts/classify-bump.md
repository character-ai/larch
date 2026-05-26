# classify-bump.sh

`classify-bump.sh` is the deterministic classifier for the dev-only `/bump-version` skill. It inspects the public plugin surface (`skills/**`, `agents/**`), writes the reasoning file, and emits `CURRENT_VERSION`, `NEW_VERSION`, `BUMP_TYPE`, and `REASONING_FILE`.

## Idempotency

The classifier treats the branch as already bumped when the idempotency head is a `Bump version to X.Y.Z` commit. Before checking that subject, it walks past up to three transparent commits from the bump pipeline: `Update CHANGELOG for X.Y.Z` commits that touch only `CHANGELOG.md`, and `chore(larch-logs): ...` commits that touch only `larch-logs/**`. Subject matches alone are not trusted.

## Edit-in-sync

Keep this file aligned with `.claude/skills/bump-version/SKILL.md`, `.claude/skills/bump-version/scripts/apply-bump.md`, `scripts/commit-changelog.md`, and `scripts/drop-bump-commit.md` when the bump/changelog commit shape changes.
