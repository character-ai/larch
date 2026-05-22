# Version Bump Reasoning

- **Base commit**: `03f517e9` (Fixes #2523: audit-runs: filter findings against in-flight/closed-with-version-window issues + narrow oos-category-mangle scan (#2533))
- **Current version**: `34.0.23`
- **Classification scope**: `skills/**` and `agents/**` only (public plugin surface).

## Result: MAJOR

- **New version**: `35.0.0`

### MAJOR evidence
- Removed `--design-classification` from argument-hint in `skills/design/SKILL.md`
- Removed `--full` from argument-hint in `skills/design/SKILL.md`
- Removed `--session-env` from argument-hint in `skills/design/SKILL.md`
- Removed `--subagent` from argument-hint in `skills/design/SKILL.md`
- Removed `--auto` from argument-hint in `skills/fix-issue/SKILL.md`
- Removed `--hard` from argument-hint in `skills/fix-issue/SKILL.md`
- Removed `--inline` from argument-hint in `skills/fix-issue/SKILL.md`
- Removed `--auto` from argument-hint in `skills/implement/SKILL.md`
- Removed `--design-only` from argument-hint in `skills/implement/SKILL.md`
- Removed `--inline` from argument-hint in `skills/implement/SKILL.md`
- Removed `--issue` from argument-hint in `skills/implement/SKILL.md`
- Removed `--no-issues` from argument-hint in `skills/implement/SKILL.md`
- Removed `--session-env` from argument-hint in `skills/implement/SKILL.md`
### MINOR evidence
- Added `--hard` to argument-hint in `skills/design/SKILL.md`
- Added `--no-dedup` to argument-hint in `skills/design/SKILL.md`
- Added `--simple` to argument-hint in `skills/design/SKILL.md`
- Added `--trivial` to argument-hint in `skills/design/SKILL.md`
- Added `--merge` to argument-hint in `skills/fix-issue/SKILL.md`
- Added `--no-dedup` to argument-hint in `skills/fix-issue/SKILL.md`
- Added `--run-id` to argument-hint in `skills/fix-issue/SKILL.md`
- Added `--run-id` to argument-hint in `skills/implement/SKILL.md`
