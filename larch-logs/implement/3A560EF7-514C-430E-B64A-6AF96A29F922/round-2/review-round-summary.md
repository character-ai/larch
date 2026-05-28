# Review Round 2

- Mode: `diff`
- 6 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: Conditional monitor_rc detection can be satisfied by comments
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Check 3 treats `monitor_rc` in shell comments on conditional opener lines as a real branch on monitor status, allowing fences to pass while never actually routing behavior through `monitor_rc`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: Docs overstate semantic routing enforced by the linter
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-foreground-markers.md` says waits are routed through `monitor_rc` conditionals, but the current lint only enforces token presence, so documentation may create false confidence.
- **Suggested revisions (informational for voters; coder decides)**:
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


### FINDING_5: Early unconditional wait can mask monitor failure before monitor_rc branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The lint allows a bare `wait "$PID"` before the first `monitor_rc` conditional, or outside the conditional entirely, so monitor timeout/failure can be masked by the writer process exit code even when a decorative later conditional mentions `monitor_rc`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Branch commingles unrelated readability linter with monitor_rc work
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The branch includes unrelated readability-preamble lint changes alongside Family B `monitor_rc` lint changes, so failures from the separate linter can block or obscure review of the monitor behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Missing negative test for monitor_rc init outside allowed window
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness lacks a fixture proving that `monitor_rc=0` placed four or more non-blank lines above the monitor is rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


