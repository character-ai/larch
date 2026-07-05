## Proposed Design Outline

### Goals
- Add a merit ("worth doing?") judgment gate to `oos-2` that fires after actuality check per item.
- Surface all proposed merit rejections in one batch at `oos-4` for operator confirmation.
- Generalize "fully stale source" to "fully discarded source" so stale + confirmed merit rejections together qualify a source for `not planned` closure.

### Non-goals
- No new Python verb or module change.
- No third "keep-tagged" tier; judgment is binary (keep or reject).
- No tightening of the OOS filing side in `/implement` or `/design`.

### Approach sketch
- Edit `oos-2` in `.claude/skills/combine-issues/SKILL.md`: after marking an item actual, apply the five-point merit rubric from the issue body; if low-merit, add to a "proposed merit rejections" list with a 1-3 sentence cause.
- Update `oos-2` summary line to report kept, stale, and low-merit counts separately.
- Edit `oos-4` to prepend the consolidated merit-rejection list before the combination scheme prompt; the operator confirms all in one batch (approve all, free-prose keep-subset, or cancel).
- After confirmation, treat confirmed merit rejections the same as stale discards for source-closure eligibility ("fully discarded source").
- Update the close comment text to say "discarded as stale or out of line with repo principles" when merit rejections contributed.

### Surfaces in scope
- `.claude/skills/combine-issues/SKILL.md` (steps `oos-2` and `oos-4`)

### Open questions
- None.
