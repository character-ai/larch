# Review Round 1

- Mode: `diff`
- 5 accepted, 4 rejected (3 exonerated)

## Accepted Findings

### FINDING_10: Cross-reference lint helper from BASH_AUTHORING.md
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `BASH_AUTHORING.md` cites the lint target but not the enforcing helper by name, making it harder to jump from authoring rules to `fence_has_family_b_pid_capture_and_wait` while debugging CI failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_11: Name enforcing helpers in docs/linting.md table
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The canonical linter table omits helper function names, so readers cannot grep directly for `fence_has_family_b_pid_capture_and_wait` or `scan_shell_file_for_family_b_wait`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Split missing-monitor and missing-wait diagnostics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: When `breadcrumb-monitor.sh` is absent, the linter reports a missing wait-after-monitor diagnostic. This misleads contributors toward wait-order fixes instead of restoring the required monitor invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Clarify Step 8+ wrapper exit 4 routing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Step 8+ exit matrix does not distinguish wrapper exit 4 caused by monitor timeout from writer stall handling. A monitor timeout with no stall tracking can be routed through the wrong cleanup/resume path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Add explicit wait-and-propagate rationale subsection
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance criteria require a dedicated `Why wait and propagate?` subsection citing incident `984F0AA4-4436-40F3-A82E-9D114C1A58B4` and naming orphan and discarded-exit-code regression risks. The current prose embeds related rationale elsewhere, making the required narrative harder to find.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


