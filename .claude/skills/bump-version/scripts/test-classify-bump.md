# test-classify-bump.sh

Offline regression harness for the idempotency walk in `.claude/skills/bump-version/scripts/classify-bump.sh`.

## Primary

`.claude/skills/bump-version/scripts/classify-bump.sh`

## Coverage

- **Test 1**: `HEAD=Bump version to X.Y.Z` → `BUMP_TYPE=NONE`.
- **Test 2**: `HEAD=Update CHANGELOG for X.Y.Z` (CHANGELOG-only diff) over `Bump version to X.Y.Z` → `BUMP_TYPE=NONE`.
- **Test 3**: `HEAD=chore(larch-logs): ...` over `Update CHANGELOG ...` over `Bump version ...` → `BUMP_TYPE=NONE` when the diff stays under `larch-logs/**`.
- **Test 4**: `HEAD=Update CHANGELOG for X.Y.Z` over ordinary feature work → non-`NONE` bump (`PATCH` in the harness fixture).
- **Test 5**: `HEAD=Update CHANGELOG for X.Y.Z` but diff touches `skills/**` → subject spoofing does not bypass public-surface classification (`MINOR` in the harness fixture).

## Edit-in-sync

- `.claude/skills/bump-version/scripts/classify-bump.sh` (idempotency walk implementation)
- `.claude/skills/bump-version/scripts/classify-bump.md`
- `scripts/commit-changelog.md` (commit shape that produces the CHANGELOG commit)
