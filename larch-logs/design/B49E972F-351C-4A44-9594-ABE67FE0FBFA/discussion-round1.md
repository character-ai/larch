## Decision 1: Include session-setup prose in scope
- **Question**: Should session-setup prose dedup be included alongside `--run-id` flag docs?
- **Resolution**: Yes — both targets are in scope. Create a shared reference for the standard session-setup output-key list and update research/SKILL.md (and optionally review/SKILL.md) to cite it.
- **Source**: user

## Decision 2: block-issue.md scope
- **Question**: Should `skills/block-issue/SKILL.md`'s inline `--run-id` mention be shortened?
- **Resolution**: Yes — include it. Shorten or replace the inline text so it no longer contributes to the n-gram score.
- **Source**: user

## Decision 3: Preserve anti-halt/NEVER blocks
- **Question**: Does the issue's anti-halt exclusion cover all blocks protected by #5788?
- **Resolution**: Yes — any block containing "NEVER", "do not write a summary", "handoff", "returning to parent", continuation reminder text, or cited by #5788 is explicitly off-limits.
- **Source**: codebase (issue body explicit exclusion)
