## Goal
Delete the /fq alias skill and remove all documentation references to it.

## Implementation Plan

### Files to delete
- `skills/fq/SKILL.md` (and empty `skills/fq/` directory)

### Files to update
- `README.md`: remove the `/fq` row from the Aliases table
- `docs/configuration-and-permissions.md`: remove `"Skill(fq)"` and `"Skill(larch:fq)"` from the permissions snippet

### Approach
Pure deletion and removal of references. CHANGELOG.md historical entries are preserved. No logic changes.

## Test plan
- Run `/relevant-checks` (pre-commit on modified files + agent-lint full repo)
- Verify no remaining `skills/fq` references outside `.git` and `CHANGELOG.md`
