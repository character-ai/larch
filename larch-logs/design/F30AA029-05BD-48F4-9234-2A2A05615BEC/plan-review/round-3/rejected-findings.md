### [Plan Review] FINDING_2

### FINDING_2: Bootstrap self-derive tests lack a negative failure case
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: The proposed test coverage validates successful self-derivation only, so regressions that skip export or tolerate an empty/broken `CLAUDE_PLUGIN_ROOT` could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a negative sandbox case asserting non-zero exit and the existing :? guard message when derivation fails


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:125-160; scripts/run-step5-review.md:3-5
- **Concern**: [SCOPE-REDUCTION] Item 4 expands the Step 5 SKILL fence with ~25 lines of dynamic_archetypes resolution and banner math instead of keeping the call site thin. Scenario: Item 4 replaces prompt-side glob bash with a tested CLI (good) but still duplicates orchestrator-facing logic that run-step5-review.sh already centralizes: the launcher sources lib-implement-round-cap.sh, reads session-env, knows STARTING_ROUND, and its contract says the goal is to keep the SKILL call site small. The expanded fence reintroduces maintenance surface and re-implements cap precedence beside an existing launcher
- **Proposed resolution**: Have run-step5-review.sh loop mode print the Step 5 breadcrumb to stderr before dispatch (using count_prior_degraded_rounds with STARTING_ROUND and the same dynamic-archetypes precedence review-and-fix uses); keep SKILL.md as rehydrate + one launcher invocation. Optionally drop the separate CLI if the launcher becomes the sole caller


