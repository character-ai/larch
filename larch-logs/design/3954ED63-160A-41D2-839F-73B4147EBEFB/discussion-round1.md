## Decision 1: Scope of the main-agent archetype fix (/implement)
- **Question**: Fix only `--emergency`, or all main-agent (`--coder claude`) coding paths?
- **Resolution**: All main-agent coding paths. The root cause is the shared `claude_fallback` path (Step 2 dispatch clears scout state and returns `claude_fallback`; Step 2.4 main-agent coding never produces the coder archetype manifest). Covers `--emergency`, both-tools-unavailable fallback, and explicit `--coder claude`.
- **Source**: user

## Decision 2: Fallback when no valid coder manifest (/implement)
- **Question**: If the main agent produces no usable archetype manifest, fall back to today's separate round-1 scout, or run static reviewers only?
- **Resolution**: Static reviewers only. Remove the separate round-1 scout on the /implement review path. The coder (external or main agent) is the sole dynamic-archetype source; when no valid coder manifest exists, that review round runs static reviewers with no dynamic archetypes.
- **Source**: user

## Decision 3: Which skills lose the separate scout (cross-skill scope)
- **Question**: The scout lives in shared review code used by `/implement`, `/design`, and `/review`. Where should the separate scout be removed?
- **Resolution**: Remove (gate off) the separate scout on the `/implement` and `/design` paths only; KEEP the scout in `/review` standalone (it has no coder/drafter and its dynamic archetypes come only from the scout). In `/design`, the agent drafting the plan proposal (the plan drafter) must do the scout's job and produce the plan-review archetypes.
- **Source**: user

## Decision 4: Failure handling when a valid manifest is not produced
- **Question**: What happens when whoever is tasked with producing the archetype manifest (main agent, Codex, Cursor, or the /design plan drafter) fails to produce a valid one?
- **Resolution**: Emit a loud warning AND surface the failure in the final report (the /implement run summary; and the equivalent surfacing for /design). Applies to ALL producers, not just the main agent. Treated as a bug needing immediate fix.
- **Source**: user

## Hard constraints (preserve)
- `/review` standalone dynamic-archetype scout behavior must remain unchanged.
- Manifest production is best-effort and must never block/stall the run; a failure degrades to static-only review for that round (plus the loud warning + report).
- The contract Step 5 review consumes (eligibility marker + `SCOUT_CODER_STATUS=ok` + `scout-coder-manifest.json`) and `scout filter-manifest` normalization must be matched exactly so the existing consumer is unchanged.
- Diff-type intentional skips (docs-only / test-only / generated-only) where dynamic archetypes are by-design absent must NOT be reported as production failures.
