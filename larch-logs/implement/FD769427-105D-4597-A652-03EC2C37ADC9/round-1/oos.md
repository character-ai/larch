### FINDING_4: [OUT_OF_SCOPE] Design anti-halt still points immediate-background fences at notifications
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bgjob-docs
- **Severity**: minor
- **Concern**: `skills/design/SKILL.md` still treats the global anti-halt paragraph as notification-driven for immediate-background fences even though the moved major steps are bgjob-migrated, so the top-level skill guidance and step-level wait contract diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-bgjob-docs: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] design-background-wait.md still reads as normative recovery prose
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bgjob-docs
- **Severity**: minor
- **Concern**: `skills/shared/design-background-wait.md` still presents notification-based recovery as the normative `/design` wait contract instead of a legacy-only compatibility path, so two authoritative wait contracts remain live.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-bgjob-docs: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Harness coverage does not pin the new bgjob NEVER literals
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `scripts/test-render-cost-line-callsites.sh` does not pin the new `orchestrator-never.md` bgjob literals or the compatibility-only narrowing, leaving prompt-text drift untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Implement closeout final-summary bindings still point at foreground stdout
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: `skills/shared/final-summary-emit.md` still describes implement closeout with foreground wrapper stdout instead of bgjob `DONE` stdout plus result env, which can make closeout look exempt from the bgjob completion gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Closure baseline changed outside the chunk scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: `python/skill-closure-baseline.json` was updated even though it was outside the chunk scope, so this looks like collateral rather than a scoped finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Tier-1 AGENTS guidance still centers notification completion
- **Reviewer(s)**: dyn-dyn-bgjob-docs
- **Severity**: minor
- **Concern**: `AGENTS.md` still centers task-notification completion for long helpers and keeps `/implement` notification-recovery text, which conflicts with the migrated bgjob-oriented skill prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-docs: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

