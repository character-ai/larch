# Version Bump Reasoning

- **Base commit**: `39c61f6` (fix(oos-cleanup): script output routing, --no-dep-llm scope, design-quick mode docs and test coverage (v20.8.4) (#1811))
- **Current version**: `22.0.0`
- **Classification scope**: `skills/**` and `agents/**` only (public plugin surface).

## Result: MAJOR

- **New version**: `23.0.0`

### MAJOR evidence
- Deleted `skills/fq/SKILL.md`

### MINOR evidence
- Added `--design-classification` to argument-hint in `skills/design/SKILL.md`
- Added `--full` to argument-hint in `skills/design/SKILL.md`
- Added `skills/report-tokens/SKILL.md`
