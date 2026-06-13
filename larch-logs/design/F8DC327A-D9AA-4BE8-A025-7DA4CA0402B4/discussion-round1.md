## Decision 1: stall-recovery-report.sh parameterization strategy
- **Question**: Should /design parameterize stall-recovery-report.sh via --profile / --artifact-prefix flags (generic mode) or add --skill design as a first-class arm?
- **Resolution**: Add generic parameterization flags (--profile generic, --artifact-prefix, --step-vocab-file or inline vocab overrides, state-file overrides). The stall-recovery-report.md explicitly defers "Public generic profile flags such as --profile generic, --artifact-prefix, state-file overrides, vocabulary overrides, and generic ledger overrides" to #3992.
- **Source**: codebase (skills/implement/scripts/stall-recovery-report.md deferred-to-#3992 note)

## Decision 2: /design terminal failure surface
- **Question**: Which /design outcomes are terminal failures (file report) vs operator actions (skip)?
- **Resolution**: Terminal failures: PLAN_WRITE_OK=false, PUBLISH_OK=false (after successful plan write), Step 3 LOOP_STATUS=postplan-failed, design-publish.sh exit 2. Operator actions (skip filing, record in chat/log): all cancelled-* outcomes. Approved paths: escalation-success filing only when escalation ledger is non-empty.
- **Source**: codebase + issue requirements

## Decision 3: /design escalation surface
- **Question**: Which /design events count as escalation (script-owned fix loop failed, handed to main agent)?
- **Resolution**: Step 3 LOOP_STATUS=main-agent-vote-required (0-judge MAV), Step 3 LOOP_STATUS=main-agent-apply-required (dedup fail in loop), validator autofix exhausted/failed/unavailable at Steps 2b/Gate-B/discussion-round2/5c.
- **Source**: codebase (SKILL.md Step 3 post-loop branch matrix, SKILL.md Plan command validator failure shared section)

## Decision 4: teardown gate location
- **Question**: Where does the /design failure-report gate run — inside render-final-summary.sh or as a new pre-step?
- **Resolution**: Inside render-final-summary.sh --post-publish-only phase (after outcome is known), analogous to Step 18a.5 running "before Step 18b and outside the active STALL_TRACKING gate." This is the unified terminal point for all /design run paths.
- **Source**: codebase (render-final-summary.sh --pre-publish-only / --post-publish-only split; SKILL.md Step 18a.5 for implement analog)
