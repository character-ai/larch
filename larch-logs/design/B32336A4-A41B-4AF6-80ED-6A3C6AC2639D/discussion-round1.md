## Decision 1: Scope — which skills are affected
- **Question**: Does this change apply to all four skills (/design, /implement, /review, /research)?
- **Resolution**: Yes — the user said "any other skills", and codebase shows all four call `degraded-tools-gate.sh`. The `skills/shared/external-reviewers.md` "Degraded-tools gate (Step 0)" procedure is the canonical shared caller contract and must also be updated.
- **Source**: codebase + user request

## Decision 2: "Both unavailable" threshold
- **Question**: What counts as "both unavailable"?
- **Resolution**: Both tools have `STATE != ok` (codex_state not-ok AND cursor_state not-ok). Matches the existing `DEGRADED=true` condition but with both tools down.
- **Source**: codebase (degraded-tools-gate.sh lines 99-102)

## Decision 3: Non-interactive/autonomous behavior
- **Question**: Should the "both down" case block on autonomous/cron runs?
- **Resolution**: No change. Autonomous runs already proceed without asking for all DEGRADED cases. This change only affects interactive runs.
- **Source**: codebase (external-reviewers.md §Degraded-tools gate) + user request scope
