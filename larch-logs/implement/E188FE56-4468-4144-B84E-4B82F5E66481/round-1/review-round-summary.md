# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Incidental security prose bypasses disposition gating
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Description prose containing `focus-area = security` is classified as security-routed, while the documented and former tested contract treats prose-only mentions as non-security. An accepted OOS block can therefore bypass required disposition handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Align oos-disposition-gate.md with runtime and test, or narrow is_security_block_text() to field lines only and update the pytest expectation to exit 1.
  - From codex-specialist-correctness: Restore the exit-1 assertion and narrow python/larch/review/review_types.py security matching to dedicated focus-area fields.
  - From cursor-specialist-edge-cases: Restore exit-1 contract coverage: fix is_security_block_text to ignore description prose tokens, or add a failing contract test and tracked follow-up while keeping runtime unchanged only if explicitly accepted.
  - From codex-specialist-edge-cases: Constrain security detection to explicit fields and restore the exit-1 regression assertion
  - From cursor-specialist-testing: Restore exit-1 assertion and fix is_security_block_text to ignore prose-only tokens, or update the written contract and parity map if runtime change is intentional.
  - From codex-specialist-testing: Restore the exit-1 regression assertion and restrict gate security classification to dedicated focus-area fields.


### FINDING_6: Exact stream passthrough is not verified
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Command substitution strips trailing newlines, so the delegation smoke test does not verify exact stdout and stderr bytes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Capture streams to files and compare exact bytes.


### FINDING_9: Legacy disposition-gap logging assertions are incomplete
- **Reviewer(s)**: dyn-dyn-harness-parity
- **Severity**: minor
- **Concern**: The legacy FINDING disposition-gap test omits assertions that `oos-disposition-gate` appears in `execution-issues.md` and that `step-8-oos-checkpoint-validation` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-harness-parity: Mirror the disposition-gap assertions in the legacy test: `assert "oos-disposition-gate" in issues` and `assert "step-8-oos-checkpoint-validation" not in issues`.
