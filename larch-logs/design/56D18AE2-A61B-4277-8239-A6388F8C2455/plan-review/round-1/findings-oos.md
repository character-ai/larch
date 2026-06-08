### OOS_1:
- **Description**: Voter panel is never pruned; only reviewer dispatch slots are. Scenario: Every pruned round still launches the full Claude+external judge set, so a large share of review tokens (especially Claude voters) may remain even when all reviewer combos are dropped
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/tally-code-votes.sh:788-810
- **Phase**: design

### OOS_2:
- **Description**: Label normalization will be reimplemented in bash instead of sourcing collect-findings.sh / aggregate-findings.sh helpers. Scenario: Divergent suffix/parenthetical rules would drive accepted_count=0 and silent over-pruning in later rounds
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/reviewer-prune.sh:NEW
- **Phase**: design

### OOS_3:
- **Description**: Scout/dynamic synthesis still runs before filter on rounds 3-4. Scenario: Dynamic scout + prompt synthesis cost is paid even when every combo will be pruned or when only a subset will launch; Part B savings are reviewer-launch only
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/dispatch-panel.sh:430-454
- **Phase**: design

### OOS_4:
- **Description**: Conditional spawning covers reviewer combos only not the judge/voter panel. Scenario: Voter launches (Claude + available externals) still run every round even when most reviewer slots were pruned; a large share of review tokens may remain
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/dispatch-code-voters.sh
- **Phase**: design

### OOS_5:
- **Description**: [SCOPE-REDUCTION] Overlapping fail-closed guards for dynamic-only pruned panels. Scenario: Plan adds both a review-core.sh pre-convergence guard and a new check-reviewer-failure-threshold.sh post-filter mode for the no-static-rows case — two surfaces to keep aligned
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/review/scripts/review-core.sh:606-688
- **Phase**: design

