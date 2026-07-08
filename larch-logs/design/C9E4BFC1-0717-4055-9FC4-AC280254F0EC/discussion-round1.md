## Decision 1: Disposition selection at the hard gate
- **Question**: When the high coverage-gap threshold trips (or non-empty todos_left forces a disposition), how is `proceed-partial` vs `bail-rescope` chosen, including unattended `--merge`/cron runs?
- **Resolution**: Always an operator decision via `AskUserQuestion` (proceed-partial / bail-rescope). Prompt and **wait indefinitely** for the operator — **no time-out**, no mechanical default, no unattended fail-closed fallback. On the AskUserQuestion no-response platform fallback, re-fire the identical prompt without a cap (per shared NEVER: a 60s fallback is not an answer). The run parks until a real answer arrives.
- **Source**: user

## Decision 2: Concrete gate thresholds
- **Question**: What are the concrete band cutoffs, measured as untouched firm headings vs the Step-0 materialized plan?
- **Resolution**: Use the issue's example bands. Middle band = untouched firm headings >= 20% of plan OR >= 10 headings -> force-inject `larch:reviewer-plan-fidelity` into every Step 5 round (exempt from pruning, all tiers). High band = untouched >= 50% OR >= 30 -> hard-gate the ship path (ship pre-driver refuses until a recorded disposition exists). Below the middle band = today's advisory warning only. Threshold constants live in `python/larch/core/config.py` with rationale comments.
- **Source**: user

## Decision 3: Non-empty todos_left is an independent disposition trigger
- **Question**: Does non-empty manifest `todos_left` on `STATUS=complete` independently require a recorded disposition, even when firm-heading coverage is otherwise complete?
- **Resolution**: Yes. Any non-empty `todos_left` on a `STATUS=complete` manifest independently requires a disposition (at minimum a `proceed-partial` record + auto-filed follow-up), regardless of heading coverage. It must not be droppable by omission; it flows into the disposition, final summary, and PR body automatically.
- **Source**: user

## Decision 4: The gate is purely mechanical (hard constraint)
- **Question**: How much judgment may the gate exercise?
- **Resolution**: Mechanical only — counts, thresholds, and a recorded disposition. NEVER #7 (no mid-run scope re-litigation of *what to build*) stays. The disposition prompt is a binary operational choice about a mechanically-detected gap, not subjective scope judgment. No subjective mid-run scope judgment is reintroduced.
- **Source**: issue (non-goals)

## Decision 5: Do not change implementer dispatch / one-shot contract (non-goal boundary)
- **Question**: Is the external implementer dispatch or the one-shot contract in scope?
- **Resolution**: No. Out of scope. Oversized plans at the source are handled by the companion /design plan-size guardrail issue. This work only measures the returned artifact against the plan and gates on the result.
- **Source**: issue (non-goals)

## Decision 6: Anti-gaming coverage basis (hard constraint)
- **Question**: What is coverage compared against?
- **Resolution**: Coverage compares the manifest's touched paths against the plan's firm headings **as materialized at Step 0**, never against acceptance checks whose inputs the implementation can rewrite (allowlists, baselines, skip markers). Firm headings = non-conditional headings (`NEW:`/`UPDATED:`, and `REWRITTEN:`); `MAY_UPDATE:` is conditional and excluded. Exact firm-set to be aligned with the existing Step-2 coverage probe during drafting.
- **Source**: issue (proposed mechanic 5)
