# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Standalone `!` prefixes are not peeled
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Negated grep-family commands at segment starts are skipped because prefix peeling does not consume a standalone `!`. That lets `! rg ... ../root` and `false || ! grep ...` evade the parent-ascent and no-path checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Treat ! like if when peeling command prefixes and add regression tests for !-prefixed grep-family lines


### FINDING_2: Quoted `|&` is not recognized as a boundary token
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: The quoted-operator guard omits the new `|&` separator, so quoted pipe-stderr tokens are treated like path operands instead of boundary tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Extend is_quoted_operator_operand() to cover quoted |&, or replace the hard-coded set with a shared boundary-token predicate that includes every separator the scanner recognizes.


### FINDING_4: Same-line clause-headed commands can still skip the scan restart
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: The line scanner restarts only on shell separators, so same-line clause-headed commands such as `if ...; then rg ...; fi` can bypass the no-path and parent-ascent checks by skipping past the clause opener.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Keep scanning past non-grep segment starts instead of jumping straight to the next separator, or explicitly restart after clause keywords that open same-line command lists, and add a regression test for a then-headed case.


