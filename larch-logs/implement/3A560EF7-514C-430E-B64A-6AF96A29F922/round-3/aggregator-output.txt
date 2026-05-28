### FINDING_1: Conditional scan stops before later valid monitor_rc branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Check (3) returns failure on the first if/case opener that does not reference monitor_rc, so fences with an unrelated guard before a later valid monitor_rc branch false-fail as missing conditional branching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Heredoc detection rescans quadratically
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: line_is_heredoc_body_idx rescans from line 0 for each call, adding O(n^2) work for large fenced examples during the new monitor_rc walks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: monitor_rc init rejects inline shell comments
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The monitor_rc initialization window checks the raw line against the init regex, so valid lines like monitor_rc=0 with a trailing shell comment are rejected even though similar capture lines strip comments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Decorative monitor_rc conditional can allow later bare wait
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Check (3) accepts any monitor_rc if/case before a wait, without proving the captured writer wait is inside the monitor_rc-controlled branch; a decorative conditional followed by a bare wait can still mask monitor failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Plan-supported conditional forms are rejected
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The implementation recognizes only if/case openers, while the plan mentions additional conditional forms such as elif, while, and until; valid fences using those forms may false-fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: case monitor_rc handling lacks a positive test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness does not include a positive fixture for case "$monitor_rc" in, so future changes could break implemented case-opener handling without test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] lint-readability-preamble is coupled to this lint surface
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The branch bundles lint-readability-preamble into the same lint and pre-commit surface as lint-foreground-markers, so unrelated readability manifest issues can fail the full lint target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: monitor_rc token check accepts quoted literal text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The conditional check accepts literal quoted text containing monitor_rc rather than requiring shell expansion, so a fence can pass with a condition like if [ "monitor_rc" = "monitor_rc" ] while ignoring actual monitor failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Failure branch need not exit with monitor_rc
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The lint checks for required tokens but does not require the monitor-failure path to exit with monitor_rc, allowing a block to pass while still exiting 0 after monitor timeout if the writer wait succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Per-anchor suppression bypasses monitor_rc enforcement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A lint-foreground-markers: ok suppression on an anchor suppresses all monitor_rc checks, so mistaken or malicious suppressions can bypass the new enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: monitor_rc init accepts nonzero numeric values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The initialization regex accepts monitor_rc=N for any digits, so monitor_rc=1 can pass even though the canonical initialization appears to be monitor_rc=0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
