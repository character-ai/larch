# test-classify-bump.sh

Offline regression harness for the idempotency walk in `.claude/skills/release/scripts/classify-bump.sh`.

## Primary

`.claude/skills/release/scripts/classify-bump.sh`

## Coverage

- `HEAD=Bump version to X.Y.Z` → `BUMP_TYPE=NONE`.
- `HEAD=chore(larch-logs): ...` over `Bump version ...` → `BUMP_TYPE=NONE` when the diff stays under `larch-logs/**`.
- Transparent-subject spoofing does not bypass public-surface classification when the diff touches `skills/**`.
- `--base` skips idempotency for release-window classification.
- `--head` scopes classification to the explicit head ref.

## Edit-in-sync

- `.claude/skills/release/scripts/classify-bump.sh`
- `.claude/skills/release/scripts/classify-bump.md`
- `.claude/skills/release/scripts/release-prepare.sh`
