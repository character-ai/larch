# Review Round 1

- Mode: `diff`
- 5 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_2: comment-only monitor_rc references satisfy conditional detection
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Comment lines containing `monitor_rc` can satisfy the conditional scan, allowing fences with no executable monitor_rc branch to pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_4: missing positive fixture for backslash-continued monitor capture
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The harness lacks a positive test for the production-shaped backslash-continued `breadcrumb-monitor.sh ... || monitor_rc=$?` form, so continuation merge regressions could pass the unit harness while failing canonical SKILL fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: case 56 does not exclude extra monitor_rc diagnostics
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Case 56 only checks for the init diagnostic, so false-positive init walking could emit all three monitor_rc errors without failing the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: missing negative fixture for absent monitor_rc capture
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no dedicated negative fixture where init and branch are present but `|| monitor_rc=$?` is missing, leaving capture-regex regressions under-covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: missing negative fixture for decorative conditional/comment bypass
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The harness lacks a negative regression fixture for a bare wait followed by an unrelated conditional or `# monitor_rc` comment, so weak conditional matching could return unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


