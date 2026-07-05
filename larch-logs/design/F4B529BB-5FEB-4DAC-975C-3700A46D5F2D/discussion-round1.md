## Decision 1: Scope of changes
- **Question**: Which files does this touch?
- **Resolution**: `.claude/skills/combine-issues/SKILL.md` only — steps `oos-2` and `oos-4`. No Python changes. No tests currently pin `oos-2` summary text.
- **Source**: codebase

## Decision 2: Merit check placement in oos-2
- **Question**: Where does the merit gate fire within oos-2 per-item flow?
- **Resolution**: After the actuality check (file-existence + concern-still-present). Only items that pass actuality (are not stale, not blocked) go through the merit gate.
- **Source**: issue body

## Decision 3: Merit rejection staging
- **Question**: When are merit rejections surfaced to the operator?
- **Resolution**: Held through oos-3 and proposed alongside the combination scheme in oos-4 as a consolidated list. Not auto-discarded. One batch confirmation covers all.
- **Source**: issue body

## Decision 4: Fully-discarded source closure
- **Question**: Does "fully discarded" include merit rejections for source closure in oos-4 and oos-7?
- **Resolution**: Yes. After operator confirms merit rejections in oos-4, a source whose every item is either stale or confirmed-merit-rejected qualifies for `not planned` closure with an honest comment. Same close-stale path.
- **Source**: issue body
