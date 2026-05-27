### FINDING_1: Step 1e can still run on first-time outline path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-routing-completeness-output.txt
- **Severity**: important
- **Concern**: Step 1e remains physically between Step 1d.7 and Step 2a, prints the Gate A breadcrumb/timing, loads approval-gates.md, and can execute Gate A body even on first-time outline-approved/pre-plan paths that should skip Gate A entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-routing-completeness-output.txt: Address the concern above.

### FINDING_2: Step 1d.7 handoff is not explicit enough to bypass Step 1e
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The anti-halt sequence says 1d.7 proceeds to 2a, but SKILL.md file order places Step 1e between them and the 1d.7 block lacks an explicit post-approval jump, so a sequential agent may enter Step 1e after outline approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Step 1d sprawl split-path still routes to Gate A
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-routing-completeness-output.txt
- **Severity**: important
- **Concern**: SKILL.md’s Step 2b.5 split-path return still routes Step 1d sprawl to Step 1e Gate A, while decompose-panel.md routes the same path to Step 1d.7 outline approval. This can bypass the new first-time outline gate or land on the wrong prompt surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-routing-completeness-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Step 3 outline merge is prose-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-routing-completeness-output.txt
- **Severity**: latent
- **Concern**: design-outline.md says Step 3 may merge outline context, but plan-review-loop.sh has no corresponding implementation. Reviewers may not see approved outline context unless it is reflected indirectly in the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-routing-completeness-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Design-outline publish contract conflicts with acceptance text
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sentinel-guard-completeness-output.txt
- **Severity**: important
- **Concern**: The landed contract allows design-outline.md to appear in redacted design-log publish artifacts, while acceptance or issue-plan wording still says the outline is excluded from the publish bundle. Operators may treat the stale acceptance text as normative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sentinel-guard-completeness-output.txt: Address the concern above.

### FINDING_6: Step 2a/2b outline consumption prose lacks structure-test pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Check 2974 pins .outline-approved behavior but not the SKILL.md prose that injects approved outline context into Step 2a/2b. Future edits could remove approved-direction substitution while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Step 0b ad-hoc Q&A exclusion lacks SKILL.md pin
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The ad-hoc Q&A-only exclusion is pinned in design-outline.md but not in SKILL.md. Removing the SKILL.md exclusion could allow already-planned Q&A runs to enter Step 1d.7 while tests remain green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Approved outline can amplify prompt injection into external reviewers
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Approved outline content is injected into external sketch/dialectic prompts as binding direction, so malicious issue or refine text can become authoritative unless operators are warned to review it carefully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Refine loop lacks explicit no-secrets guidance
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: design-outline.md may be captured in redacted design logs, but operators may still paste secrets into Refine input if the loop does not warn that outline artifacts are not a secrecy boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: Outline fan-out lacks bounded digest guidance
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: There is no mechanical cap or bounded-digest instruction before sending approved outline text to parallel external sketch slots, which can increase cost and failure rates for large outlines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Gate B/C re-entry lacks a persisted marker
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 1e treats plan.txt as sufficient to stay on the post-plan gate path, but there is no persisted marker proving control actually arrived from Gate B(c) or Gate C(b). A resumed agent with plan.txt may execute Gate A outside true re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_16: [OUT_OF_SCOPE] CHANGELOG still describes stale brainstorm/Gate A flow
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-routing-completeness-output.txt
- **Severity**: nit
- **Concern**: CHANGELOG.md still says brainstorm runs before Gate A and does not mention Step 1d.7, which is stale consumer-doc flow text outside the runtime diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-routing-completeness-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Downstream outline consumption triple-condition is consistent
- **Reviewer(s)**: dyn-sentinel-guard-completeness-output.txt
- **Severity**: nit
- **Concern**: Downstream outline consumption consistently requires design-outline.md to be non-empty and `.outline-approved` to exist across the reviewed files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-guard-completeness-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Step 1d.7 guard description omits plan.txt split
- **Reviewer(s)**: dyn-sentinel-guard-completeness-output.txt
- **Severity**: nit
- **Concern**: SKILL.md says the entry guard skips when `.outline-approved` exists, but omits the newer plan.txt split. This is misleading prose, though not a runtime shell bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-guard-completeness-output.txt: Address the concern above.

### FINDING_19: render-final-summary fallback formats cancelled-outline notes differently
- **Reviewer(s)**: dyn-note-file-integration-output.txt
- **Severity**: latent
- **Concern**: compose_self_fallback appends the cancelled-outline cancel-site line immediately after the sentinel, while the primary render path inserts a blank line before note-file content. Renderer-failure summaries therefore differ by one newline and the fallback parity is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-note-file-integration-output.txt: Address the concern above.

### FINDING_20: render-final-summary can pass stale note file after failed removal
- **Reviewer(s)**: dyn-note-file-integration-output.txt
- **Severity**: latent
- **Concern**: For non-cancelled-outline outcomes, invoke_render always passes --note-lines-file and silently ignores rm failure. If a stale final-summary-notes.md cannot be removed, later summaries can include prior cancel-site text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-note-file-integration-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] note-lines-file option is correctly wired for common path
- **Reviewer(s)**: dyn-note-file-integration-output.txt
- **Severity**: nit
- **Concern**: --note-lines-file is declared and matches the caller’s argument name, and missing files are ignored safely when rm succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-note-file-integration-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] primary-path test does not exercise fallback parity
- **Reviewer(s)**: dyn-note-file-integration-output.txt
- **Severity**: nit
- **Concern**: test-render-final-summary.sh validates cancel-site content and sentinel ordering only on the primary path, not fallback plus cancelled-outline parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-note-file-integration-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] render-final-summary lacks implement-style cost-unavailable reinvoke
- **Reviewer(s)**: dyn-note-file-integration-output.txt
- **Severity**: nit
- **Concern**: render-final-summary.sh does not have the implement-style stage-1 --cost-unavailable reinvoke before compose_self_fallback; this asymmetry predates the branch and is outside note-file integration scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-note-file-integration-output.txt: Address the concern above.
