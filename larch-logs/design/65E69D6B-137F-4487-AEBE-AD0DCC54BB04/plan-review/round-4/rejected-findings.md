### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1011, skills/design/scripts/dispatch-plan-review-panel.sh:168-230, skills/design/scripts/render-plan-review-prompt.sh:105-106
- **Concern**: Scout/prompt changes add another scope-control reviewer lane even though SIMPLE and static Pragmatic/Innovation already cover scope creep. Scenario: The plan can spawn extra dynamic specialists and more findings for the same minimum-change concern, increasing review churn instead of reducing ratcheting
- **Proposed resolution**: Remove the scout wrapper/prompt archetype changes; pass the original issue anchor to the existing static reviewers and voters only


### [Plan Review] FINDING_16

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-marker-contract
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/aggregate-findings.sh:174-632
- **Concern**: Aggregate validation may duplicate marker parsing outside the canonical detector. Scenario: The plan makes check-scope-reduction-marker.sh canonical, but aggregate-validate.py is an embedded validator; reimplementing extraction there can drift from tally and dedup on fenced inline or heading cases
- **Proposed resolution**: Have plan-mode aggregate validation invoke the helper on temp block files, or factor a shared implementation used by both the helper and validator


