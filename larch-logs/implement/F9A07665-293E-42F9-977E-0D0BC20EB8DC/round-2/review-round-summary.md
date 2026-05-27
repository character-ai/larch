# Review Round 2

- Mode: `diff`
- 6 accepted, 9 rejected (8 exonerated)

## Accepted Findings

### FINDING_12: Step 2a.5 outline prepend is optional while other consumers require it
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 2a.5 says the dialectic may prepend approved outline context, while Steps 2a and 2b require it under the approved-outline conditions. Dialectic may ignore operator-approved direction that sketches and plan honor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Outline entry guard does not cover missing sentinel with existing plan
- **Reviewer(s)**: dyn-sentinel-guard-completeness-output.txt
- **Severity**: important
- **Concern**: design-outline.md’s entry guard does not explicitly handle `.outline-approved` absent while plan.txt exists. That state falls into the full approval prompt, whose Approve path proceeds to Step 2a, potentially duplicating sketch/dialectic work after a plan is already materialized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-guard-completeness-output.txt: Address the concern above.


### FINDING_14: Approved-outline plus existing-plan skip path lacks explicit successor
- **Reviewer(s)**: dyn-sentinel-guard-completeness-output.txt
- **Severity**: important
- **Concern**: When both `.outline-approved` and plan.txt exist, the guard says to continue on the existing post-plan gate path and not re-enter Step 2a, but does not name the next step. The anti-halt chain still lists 1d.7→2a, so a literal agent may re-enter Step 2a anyway.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-guard-completeness-output.txt: Address the concern above.


### FINDING_15: Step 1e and Step 1d.7 disagree on plan-without-outline behavior
- **Reviewer(s)**: dyn-sentinel-guard-completeness-output.txt
- **Severity**: important
- **Concern**: Step 1e treats plan.txt presence as enough to run the post-plan Gate A path, while Step 1d.7 can still require outline approval when `.outline-approved` is missing. A mis-route can therefore run Gate A without ever forcing outline approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-guard-completeness-output.txt: Address the concern above.


### FINDING_20: render-final-summary can pass stale note file after failed removal
- **Reviewer(s)**: dyn-note-file-integration-output.txt
- **Severity**: latent
- **Concern**: For non-cancelled-outline outcomes, invoke_render always passes --note-lines-file and silently ignores rm failure. If a stale final-summary-notes.md cannot be removed, later summaries can include prior cancel-site text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-note-file-integration-output.txt: Address the concern above.


### FINDING_3: Step 1d sprawl split-path still routes to Gate A
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-routing-completeness-output.txt
- **Severity**: important
- **Concern**: SKILL.md’s Step 2b.5 split-path return still routes Step 1d sprawl to Step 1e Gate A, while decompose-panel.md routes the same path to Step 1d.7 outline approval. This can bypass the new first-time outline gate or land on the wrong prompt surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-routing-completeness-output.txt: Address the concern above.


