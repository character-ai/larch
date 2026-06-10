## Decision 1: Combined archetype name for /implement and /review
- **Question**: Should the combined security+edge-cases slot keep the name `edge-cases` or get a new name?
- **Resolution**: Keep `edge-cases` — backward-compatible with existing filename conventions and test harnesses; update the agent description to make security a co-primary focus.
- **Source**: codebase (dispatch-panel.sh derives agent from name: `reviewer-${name}.md`; keeping the name avoids renaming all output files and test fixtures)

## Decision 2: Handle reviewer-security.md after removal from static list
- **Question**: Should `agents/reviewer-security.md` be deleted after removing security from the static list?
- **Resolution**: Keep the file — test harnesses directly check its existence and structure. Deleting it would break those tests.
- **Source**: codebase (scripts/test-review-structure.sh line 343 checks reviewer-security in specialist list)

## Decision 3: Data-driven refactor for dispatch-plan-review-panel.sh
- **Question**: Should the hardcoded archetype loops be refactored to a variable?
- **Resolution**: No — just remove `edge` from the hardcoded lists (minimal diff, operator choice).
- **Source**: user

## Decision 4: sketch_budget for HARD after removing Edge slot
- **Question**: After removing Cursor-Edge sketch, should sketch_budget change from 4 to 3?
- **Resolution**: Yes — update valid values in python/session_env.py to include 3, update SKILL.md to say 3-slot regular mode.
- **Source**: codebase (session_env.py validates sketch_budget against {"0","2","4"})
