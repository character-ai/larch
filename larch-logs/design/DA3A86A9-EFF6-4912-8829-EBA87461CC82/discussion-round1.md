## Decision 1: Scope is exactly the two standalone Bash fences
- **Question**: Is the change scoped strictly to the Step 4 `ACTION=FINALIZE` turn and the Step 2a SIMPLE-branch sketch-sentinel writes, or should other similar standalone-turn fences be folded too?
- **Resolution**: Strictly the two fences named in the issue. No scope expansion to other steps.
- **Source**: codebase (issue body "The two fences removed as standalone turns")

## Decision 2: Behavior must be preserved exactly
- **Question**: What must not break?
- **Resolution**: (a) `rejected-findings.md` / `accepted-plan-findings.md` / `oos.md` (and `voting-tally.md`) still guaranteed to exist before Step 5; (b) FINALIZE's validation of non-empty `plan.txt` + `diff-lines.txt` still surfaces a repairable failure; (c) SIMPLE sketch sentinels (`NO_SKETCHES_CLASSIFIED_SIMPLE` -> approach-synthesis.txt, `NO_CONTESTED_DECISIONS` -> contested-decisions.md, empty dialectic-resolutions.md) still written on the SIMPLE branch; (d) idempotency under pause/resume preserved.
- **Source**: codebase (issue Scope/acceptance + finalize-plan.sh)

## Decision 3: FINALIZE fold target left to the plan
- **Question**: Pin the FINALIZE fold target (Step 3b boundary vs Gate C preview) or let the plan decide?
- **Resolution**: Let the plan decide. Pick the cleanest ordering-safe fold (FINALIZE touch must precede Step 4's rejected-findings read, or Step 4's read must become absence-tolerant). Review panel vets it.
- **Source**: user (Step 1c AskUserQuestion)

## Decision 4: Test + lint acceptance
- **Question**: What is "done"?
- **Resolution**: Both fences removed as standalone orchestrator turns; `test-design-structure.sh` sentinel/finalize assertions updated to match; affected harnesses + `make lint` green.
- **Source**: codebase (issue Scope/acceptance)
