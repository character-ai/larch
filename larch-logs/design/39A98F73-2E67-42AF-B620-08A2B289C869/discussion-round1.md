## Decision 1: Durable scope of #3195 given the breadcrumbs removal
- **Question**: #3119/#3120 delete the breadcrumbs machinery but preserve the polling-loop ban. What should #3195 deliver?
- **Resolution**: Strengthen the anti-polling rule independently (do NOT block on #3119/#3120). Add a machinery-independent clause that bans manual per-turn reads of a background task's output file and requires ending the turn to wait for the Bash `<task-notification>`. The current `AGENTS.md` polling rule names `for`/`while`/`until`+`sleep` loops and `ScheduleWakeup`, but NOT the per-turn-file-read shape that caused the incident — that gap is the durable fix. Scope = SIMPLE (prose only).
- **Source**: user

## Decision 2: Placement strategy to stay compatible with #3119
- **Question**: How to add the clause without colliding with #3119's rewrite of the same files?
- **Resolution**: Place the clause OUTSIDE #3119's blast radius. (a) New SELF-CONTAINED Conventions bullet in `AGENTS.md`, separate from the entangled line-57 bullet, with zero breadcrumb tokens. (b) Strengthen the canonical narrative in `skills/shared/orchestrator-never.md` (which #3119 only trims, not deletes). NEVER #9 already references orchestrator-never.md as canonical, so the discipline propagates without editing the breadcrumb-entangled `implement/SKILL.md` NEVER #9/#16 blocks. Do NOT touch those NEVER blocks (that was Option C — rejected as collision-prone and redundant).
- **Source**: user + codebase (AGENTS.md:57, orchestrator-never.md, implement/SKILL.md grep)

## Decision 3: Disposition of breadcrumb-specific Fix A and Fix C
- **Question**: How to handle Fix A (change breadcrumb-monitor.sh sentinel semantics) and Fix C (lint for competing monitors)?
- **Resolution**: Drop both. Note in the plan that #3119/#3120 eliminate the Part 1 trigger entirely (no monitor, no sentinel to race). No OOS issue filed.
- **Source**: user

## Decision 4: Fix B disposition
- **Question**: Fix B proposed a NEVER rule banning a second `breadcrumb-monitor.sh`. Keep it?
- **Resolution**: Generalize, do not keep verbatim. The breadcrumb-specific "second monitor" rule dies with the machinery. Its durable kernel — "after launching a background task, rely on the task-notification; never poll" — is folded into Decision 1's machinery-independent clause.
- **Source**: codebase + user directive

## Hard constraints
- Phrasing MUST be machinery-independent: no `breadcrumb-monitor.sh`, `LARCH_DONE_SENTINEL`, FD-3, or BASH_AUTHORING.md §4 tokens in the new clause, so it survives #3119/#3120.
- MUST NOT add code to the breadcrumb subsystem (no Fix A, no Fix C lint).
- MUST NOT block on #3119/#3120 landing.
- Preserve the existing meaning of the AGENTS.md polling rule and the NEVER #9 reference chain.
