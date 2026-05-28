### FINDING_1: Conditional monitor_rc detection can be satisfied by comments
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Check 3 treats `monitor_rc` in shell comments on conditional opener lines as a real branch on monitor status, allowing fences to pass while never actually routing behavior through `monitor_rc`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Multiline monitor_rc conditionals can false-fail
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Check 3 only inspects the conditional keyword line, so valid multiline or continuation-style `if`/`case` conditionals that reference `monitor_rc` on following lines can fail lint despite matching the intended Family B shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Heredoc body detection repeatedly rescans each fence
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `line_is_heredoc_body_idx` performs repeated from-start scans and duplicates heredoc state logic, creating avoidable O(n^2) work and possible drift between lint passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: NEG-A lacks stderr absence assertions
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Case 54 does not assert absence of unrelated diagnostics, so regressions that emit extra second or third errors could pass the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Early unconditional wait can mask monitor failure before monitor_rc branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The lint allows a bare `wait "$PID"` before the first `monitor_rc` conditional, or outside the conditional entirely, so monitor timeout/failure can be masked by the writer process exit code even when a decorative later conditional mentions `monitor_rc`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: while/until can satisfy monitor_rc branching without canonical two-branch handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Check 3 accepts `while`/`until` as monitor_rc branching keywords, allowing non-canonical loops to satisfy the token check without the intended `if`/`case` two-branch exit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: Branch commingles unrelated readability linter with monitor_rc work
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The branch includes unrelated readability-preamble lint changes alongside Family B `monitor_rc` lint changes, so failures from the separate linter can block or obscure review of the monitor behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Harness does not smoke-test live canonical fences
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-lint-foreground-markers` only lints temporary fixtures, so regressions in real SKILL/reference fences can pass the harness until broader repo lint or pre-commit runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Missing negative test for monitor_rc init outside allowed window
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness lacks a fixture proving that `monitor_rc=0` placed four or more non-blank lines above the monitor is rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Missing negative test for non-literal monitor_rc initialization
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The tests do not cover rejection of `monitor_rc=$?` as an initialization form, leaving room for future ERE loosening to admit non-literal initialization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] test-background-monitor-wait plan item not evidenced
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan lists `test-background-monitor-wait`, but the branch does not modify it, so that pre-merge checklist item is not evidenced in the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Multiline monitor_rc conditional scan remains a known tradeoff
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Keyword-line-only conditional scanning may false-fail rare multiline `if` headers where `monitor_rc` appears only on a continuation line; the source marked this as a pre-existing/out-of-scope tradeoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Missing exit propagation allows monitor failure to exit 0
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The lint checks for token presence but does not require failure-path exit propagation such as `exit "$monitor_rc"` or `exit "$writer_rc"`, so a fence can branch yet still suppress monitor failure with `wait ... || true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Positive fixtures omit production-style failure exits
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Clean harness fixtures omit canonical `exit "$monitor_rc"` behavior used by production SKILL fences, so future authors could copy passing test shapes that still preserve monitor-failure exit-0 behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Docs overstate semantic routing enforced by the linter
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-foreground-markers.md` says waits are routed through `monitor_rc` conditionals, but the current lint only enforces token presence, so documentation may create false confidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Structural two-branch verification remains deferred
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Full structural verification of branch exits and wait placement was deferred by the plan, leaving token-complete but semantically hollow fences possible as a known follow-up risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
