## Proposed Design Outline

### Goals
- Close the durable bug from the #3175 incident: stop the orchestrator from falling into manual per-turn polling after a background task launch.
- Name the missing failure shape explicitly — repeated per-turn reads of a background task's output file (the current rule names only `sleep`-loops and `ScheduleWakeup`).
- Keep the fix machinery-independent so it survives the #3119/#3120 breadcrumbs removal.

### Non-goals
- No change to `breadcrumb-monitor.sh` sentinel semantics (Fix A) — superseded by #3119/#3120.
- No new lint for competing monitors (Fix C) — superseded; the trigger ceases to exist.
- No edits to the breadcrumb-entangled `NEVER #9`/`#16` blocks in `skills/implement/SKILL.md` (#3119's churn zone).
- No blocking on #3119/#3120 landing.

### Approach sketch
- Add one self-contained Conventions bullet to `AGENTS.md`, separate from the breadcrumb-entangled line-57 bullet, with zero breadcrumb tokens.
- Strengthen the canonical narrative in `skills/shared/orchestrator-never.md` to name the per-turn-read shape and the "end the turn, wait for `<task-notification>`" remedy.
- Rely on NEVER #9's existing pointer to orchestrator-never.md to propagate the discipline (no NEVER-block edits).

### Surfaces in scope
- `AGENTS.md` (Conventions section)
- `skills/shared/orchestrator-never.md`
- Verification: `bash scripts/relevant-checks.sh` (or `make lint`)

### Open questions
- None.
