### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Step 1e can still run on first-time outline path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-routing-completeness-output.txt
- **Severity**: important
- **Concern**: Step 1e remains physically between Step 1d.7 and Step 2a, prints the Gate A breadcrumb/timing, loads approval-gates.md, and can execute Gate A body even on first-time outline-approved/pre-plan paths that should skip Gate A entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-routing-completeness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Outline fan-out lacks bounded digest guidance
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: There is no mechanical cap or bounded-digest instruction before sending approved outline text to parallel external sketch slots, which can increase cost and failure rates for large outlines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Gate B/C re-entry lacks a persisted marker
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 1e treats plan.txt as sufficient to stay on the post-plan gate path, but there is no persisted marker proving control actually arrived from Gate B(c) or Gate C(b). A resumed agent with plan.txt may execute Gate A outside true re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: render-final-summary fallback formats cancelled-outline notes differently
- **Reviewer(s)**: dyn-note-file-integration-output.txt
- **Severity**: latent
- **Concern**: compose_self_fallback appends the cancelled-outline cancel-site line immediately after the sentinel, while the primary render path inserts a blank line before note-file content. Renderer-failure summaries therefore differ by one newline and the fallback parity is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-note-file-integration-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Step 1d.7 handoff is not explicit enough to bypass Step 1e
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The anti-halt sequence says 1d.7 proceeds to 2a, but SKILL.md file order places Step 1e between them and the 1d.7 block lacks an explicit post-approval jump, so a sequential agent may enter Step 1e after outline approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Step 2a/2b outline consumption prose lacks structure-test pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Check 2974 pins .outline-approved behavior but not the SKILL.md prose that injects approved outline context into Step 2a/2b. Future edits could remove approved-direction substitution while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_7: Step 0b ad-hoc Q&A exclusion lacks SKILL.md pin
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The ad-hoc Q&A-only exclusion is pinned in design-outline.md but not in SKILL.md. Removing the SKILL.md exclusion could allow already-planned Q&A runs to enter Step 1d.7 while tests remain green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Approved outline can amplify prompt injection into external reviewers
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Approved outline content is injected into external sketch/dialectic prompts as binding direction, so malicious issue or refine text can become authoritative unless operators are warned to review it carefully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Refine loop lacks explicit no-secrets guidance
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: design-outline.md may be captured in redacted design logs, but operators may still paste secrets into Refine input if the loop does not warn that outline artifacts are not a secrecy boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

