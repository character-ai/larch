## Proposed Design Outline

### Goals
- Strengthen the fingerprint rule in `design-background-wait.md` so "yield" is unambiguous: end the turn with no tool call, no ScheduleWakeup, no prose.
- Document that the re-notification loop is expected behavior during a long review (process alive, `.bg-wait-active` present) and resolves automatically on process exit.
- Add a SKILL.md ANTI-PATTERN covering repeated non-empty identical notifications, closing the gap left by the existing empty-notification rule.

### Non-goals
- No code changes to `design-step3-review.sh`, hooks, or Python modules.
- No changes to the no-progress guard threshold or behavior.
- Not addressing the harness notification timing (outside larch's control).

### Approach sketch
- Update `skills/shared/design-background-wait.md` Step 3 task notification boundary: replace "yield without probing" with explicit "end the turn silently: call no tool, run no ScheduleWakeup, print no prose" for repeated identical notifications.
- Add a note below that re-notification during a long review is expected; the loop resolves when the process exits and the EXIT trap runs.
- Update `skills/design/SKILL.md` ANTI-PATTERNS: add a new rule (or extend #5) explicitly forbidding ScheduleWakeup on repeated non-empty identical notifications during any `/design` background wait.

### Surfaces in scope
- `skills/shared/design-background-wait.md`
- `skills/design/SKILL.md`

### Open questions
- None.
