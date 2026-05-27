# Review Round 2

- Mode: `diff`
- 5 accepted, 9 rejected (7 exonerated)

## Accepted Findings

### FINDING_10: SECURITY.md overstates cache touch protection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` describes the basename guard as blocking non-cache paths, which may overstate the current protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_3: Missing design-env CLAUDE_PLUGIN_ROOT rejection tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write-design-current-env.sh` now validates `CLAUDE_PLUGIN_ROOT`, but the design harness lacks rejection coverage and the stricter contract may break callers that previously relied on permissive exports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Prune harness markdown omits mtime regression cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-upgrade-larch-prune.md` omits sparse-used-versions and stat-garbage fallback cases, making key mtime regression coverage hard to discover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Session-env roundtrip contract omits sections G/H
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-session-env-roundtrip.md` documents section F but not section G/H coverage for `session-setup` and `write-design-current-env`, risking doc/test drift for touch behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: Misplaced Summary header in session-env harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-session-env-roundtrip.sh` has a `# Summary` header before later G/H tests, which misleads maintainers about the harness structure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


