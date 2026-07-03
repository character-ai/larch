## Proposed Design Outline

### Goals
- Stop `/design` from treating an `AskUserQuestion` "no response after ~60s" fallback as a real answer.
- Make every `/design` `AskUserQuestion` call site re-ask instead of guessing, so waiting becomes effectively indefinite.

### Non-goals
- Changing the underlying ~60-second platform timeout itself. That is not under this repo's control.
- Building a new pause/resume path for this case. `/larch:pause` already covers explicit operator-initiated pausing.
- Extending this rule to other skills (`/implement`, etc.) in this pass.

### Approach sketch
- Add one new NEVER rule to `skills/design/SKILL.md`'s existing `## Anti-patterns` section, a 6th rule alongside the current 5, in the same WHY / How-to-apply shape.
- Rule: when an `AskUserQuestion` result is the no-response fallback, never pick an option or infer an answer. Re-fire the identical call instead, uncapped, and stay quiet on repeat retries.
- Pin the new rule's literal text with a `contains` assertion in `scripts/test-design-structure.sh`, matching the pattern already used for the other 4 Anti-pattern rules.

### Surfaces in scope
- `skills/design/SKILL.md` (Anti-patterns section)
- `scripts/test-design-structure.sh` (new pinned assertion)

### Open questions
- None.
