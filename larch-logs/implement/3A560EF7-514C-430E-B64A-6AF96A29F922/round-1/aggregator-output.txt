### FINDING_1: monitor_rc branching can be satisfied by unrelated control flow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The monitor_rc conditional check is too token-based: unrelated `if`/loop/case blocks, comments, strings, or a bare `wait "$PID"` after monitor completion can satisfy lint while still masking breadcrumb-monitor failures. The lint should require real branching on `monitor_rc`, ensure waits/exit routing are inside the relevant branch structure, and reject line-initial waits before the qualifying conditional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: comment-only monitor_rc references satisfy conditional detection
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Comment lines containing `monitor_rc` can satisfy the conditional scan, allowing fences with no executable monitor_rc branch to pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: heredoc body detection rescans fences repeatedly
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `line_is_heredoc_body_idx` performs repeated O(n) scans inside nested loops, creating avoidable CPU cost on large fences and risking drift from related anchor scanning logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_6: repo-wide lint acceptance is not evidenced
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The review evidence does not show `make lint-foreground-markers` passing repo-wide, so canonical SKILL fences could fail the new checks if production fences or continuation handling drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: missing negative fixture for absent monitor_rc capture
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no dedicated negative fixture where init and branch are present but `|| monitor_rc=$?` is missing, leaving capture-regex regressions under-covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: monitor_rc checks are skipped when PID/wait matching fails first
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The new monitor_rc diagnostics only run after a matching wait is found, so fences with a wait/PID mismatch and missing monitor_rc tokens surface only the older mismatch diagnostic until fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: missing negative fixture for decorative conditional/comment bypass
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The harness lacks a negative regression fixture for a bare wait followed by an unrelated conditional or `# monitor_rc` comment, so weak conditional matching could return unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: lint contract prose still suggests wait-before-branch shape
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/lint-foreground-markers.md` still implies a wait after monitor completion before clarifying the canonical monitor_rc branch shape, which may lead authors to copy an invalid bare-wait pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] case 28 does not exercise new Family B monitor_rc shape
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pre-existing case 28 is marked clean while lacking the full Family B PID/background/monitor_rc shape, so it does not exercise the new monitor_rc rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] per-anchor suppression bypasses monitor_rc enforcement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Existing per-anchor lint suppression disables both old PID/wait checks and new monitor_rc enforcement, allowing careless or malicious suppressions to evade CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] heredoc scanning is quadratic on large fences
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `line_is_heredoc_body_idx` is O(n) per call inside loops, which could slow lint on very large shell wrappers, though this is not observed on typical fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] unrelated branch changes should stay out of feature-review narrative
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch includes unrelated readability preamble and run-log flush changes that should not be counted when judging issue #3025 / monitor_rc lint plan completeness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
