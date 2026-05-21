# Version Bump Reasoning

- **Base commit**: `2e37f78a` (Fixes #2481: Harden check-reviewers.sh: replace binary-only probe with runtime health probe (mutex+retry+TTL), add Option A explicit-coder bail at Step 1 (#2504))
- **Current version**: `32.0.0`
- **Classification scope**: `skills/**` and `agents/**` only (public plugin surface).

## Result: MAJOR

- **New version**: `33.0.0`

### MAJOR evidence
- Removed `--quick` from argument-hint in `skills/design/SKILL.md`
- Deleted `skills/imaq/SKILL.md`
- Removed `--quick` from argument-hint in `skills/implement/SKILL.md`
- Deleted `skills/imq/SKILL.md`
### MINOR evidence
- Added `--auto` to argument-hint in `skills/implement/SKILL.md`
