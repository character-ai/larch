## Goal
Fix two independent bugs: (1) remove duplicate step 9a.1 breadcrumb by adding an explicit `refresh-anchor.sh` code fence; (2) fix matplotlib subprocess error masking by surfacing stderr tail instead of first line.

## Implementation Plan
- `skills/implement/SKILL.md`: add explicit `refresh-anchor.sh` Bash code fence after the token/timing block in step 9a.1 anchor assembly section
- `skills/report-tokens/scripts/run-analysis.sh`: replace first-line stderr extraction with tail-of-stderr approach capped at 2000 chars

## Test plan
Run `/relevant-checks` after each change. Verify SKILL.md passes markdownlint and run-analysis.sh remains valid Python.
