## Decision 1: Fallback when reviewer-status-table.txt is absent
- **Question**: When the pre-rendered `reviewer-status-table.txt` is missing (upgrade scenario or race), what should the SKILL.md execution sites do?
- **Resolution**: Warn and skip — print `**⚠ Reviewer status table omitted: pre-rendered table not found.**` and continue. No fallback CLI verb; no round-binding prose retained in SKILL.md.
- **Source**: user
