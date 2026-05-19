## Goal
Lower the diff_lines carve-out threshold in /implement from <30 to <=3 so only truly trivial changes bypass external coders

## Implementation Plan

### Goal
Lower the "coder simplicity override" threshold in `skills/implement/SKILL.md` from `diff_lines < 30` (bypass external coder for changes under 30 lines) to `diff_lines <= 3` (bypass external coder only for truly trivial ≤3-line changes). This ensures the main agent only self-implements when the planned change is ≤3 lines; all larger changes are delegated to an external coder.

### Files to modify
- `skills/implement/SKILL.md` — all occurrences of the threshold

### Exact string changes

1. The "no carve-out" boundary: `>=30` → `>=4` (in the prose condition "Treat an absent, empty, non-integer, or `>=30` value as "no carve-out"")
2. The carve-out firing condition: `<30` → `<=3` in prose conditions (e.g. "If the parsed integer is `<30`, set `coder=claude`")
3. The breadcrumb text: `` diff_lines < 30 `` → `` diff_lines <= 3 `` (appears in breadcrumb strings like `**⚡ 1: design plan — diff_lines < 30; coder auto-set to claude (no explicit --coder).**`)
4. References like "the `diff_lines < 30` carve-out" → "the `diff_lines <= 3` carve-out"
5. The status message "auto-routed: diff_lines < 30, no explicit --coder" → "auto-routed: diff_lines <= 3, no explicit --coder"

### Approach
Use sed/Edit tool to make targeted replacements in `skills/implement/SKILL.md`. The changes are purely textual; no logic changes needed outside this file.

### Edge cases
- OOS triage policy also mentions `~30` LOC thresholds, but those refer to code-change size for out-of-scope filing decisions, NOT the coder routing threshold — do NOT touch those.
- Only change occurrences in the "Coder simplicity override + implementer waterfall" section and references to it.


## Test plan
- `grep -n "diff_lines\|>= 30\|< 30\|>= 4\|<= 3" skills/implement/SKILL.md` to confirm all threshold references updated
- `/relevant-checks` (pre-commit lint + agent-lint)
