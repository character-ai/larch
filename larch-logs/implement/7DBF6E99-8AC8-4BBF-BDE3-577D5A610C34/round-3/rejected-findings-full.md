### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Orchestrator display lacks secondary untrusted-data guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The orchestrator prints driver display before user prompting without an additional reminder/filter, so a driver sanitization bug could expose raw assessor instructions in main-agent context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: rc=10 WORSE branch has no structural guard around non-completion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The rc=10 branch is prompt-only and should not complete Step 3.6 inside the fence. A structure pin could prevent future drift where WORSE output is printed but Stop/user handling or sentinel semantics are skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `design-postplan-emit.sh` silently defaults HARD when classification helper is missing
- **Reviewer(s)**: dyn-classification-gate-output.txt
- **Severity**: latent
- **Concern**: Missing or non-executable `read-design-classification.sh` fails closed to HARD but does not add a warning, unlike the assessor driver. Operators may not know classification was unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classification-gate-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: rc=10 trailer parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: rc=10 trailer parsing exists both in `SKILL.md` and the test helper, so trailer grammar changes require synchronized edits and can drift between tests and live orchestration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: `assess-plan-round.sh` uses misleading `workflow_path` naming
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `resolve_design_classification` stores its result in a `workflow_path` variable, which can confuse readers into thinking the script still relies on legacy workflow-path semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: `design-pause-save.sh` duplicates step ordering logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Hardcoded Step 3/3.5/3.6/3b resolution duplicates the registry ordering and creates extra maintenance if substeps change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

