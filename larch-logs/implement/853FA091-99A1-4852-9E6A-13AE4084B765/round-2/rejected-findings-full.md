### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: invoke-plan-validator wrapper is not directly tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The renamed `skills/design/scripts/invoke-plan-validator.sh` is not invoked directly by any test, so wrapper piping bugs could ship even though the design-driver command path is covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: v2 run-params writer test does not enforce exact schema
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-write-run-params.sh` checks fields but does not assert the JSON contains exactly the four expected keys, allowing legacy null fields to slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: read-design-classification fallback chain lacks degraded-toolchain tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The reader harness does not test python3, jq, and grep fallback behavior, so parser regressions may only appear on production hosts missing preferred tools.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: SIMPLE reviewer emphasis may bias against material security findings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/render-plan-review-prompt.sh` tells SIMPLE reviewers to lean toward EXONERATE/addition avoidance without an explicit security carve-out, so full-panel SIMPLE runs may under-report injection, auth, or secret-handling defects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: grep fallback can mis-read classification from malformed run params
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/read-design-classification.sh` can parse `design_classification` from non-JSON substrings when python3 and jq are unavailable. Malformed or hostile run params could force SIMPLE tier, wrong caps, or weaker reviewer bias.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Gate C cap-aware options are prompt-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate C omits the rerun option only through prompt prose and does not mechanically read the counter before `AskUserQuestion`. At cap, the orchestrator may still offer “Re-run review panel,” causing a wasted short-circuit turn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Token analysis still maps legacy Quick tally text to SIMPLE
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/report-tokens/scripts/run-analysis.sh` still has a legacy Quick mode tally heuristic after Quick mode removal. A HARD run missing `timing-report.json` but containing legacy Quick tally text can be mis-bucketed as SIMPLE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicate CI focus-area anchor comments add structural noise
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` has ten duplicate CI focus-area anchor comments that do not add coverage and make Step 3 contract changes harder to review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: timing-ledger fallback ownership is undocumented
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Plan/acceptance text cites `timing-ledger.sh` for design classification fallback, but fallback logic exists only in `timing-report.sh`. Contributors may incorrectly duplicate fallback behavior into ledger code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Gate C cap breadcrumb wording diverges from Step 3 cap wording
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/approval-gates.md` and `skills/design/SKILL.md` use different wording for the review cap condition, so users may not recognize that Gate C is referring to the same locked cap state reported by Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

