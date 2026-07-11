# Review Round 2

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Require author guidance no later than the ship-blocking contract
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-gate-sequencing
- **Severity**: major
- **Concern**: G-Gate-1 uses “or later, never earlier” for both gate/producer sequencing and author guidance. That permits a new ship-blocking contract to become enforceable before authors receive the guidance needed to satisfy it, recreating the #6882 failure mode. Keep “same change or release … or later, never earlier” for gate-after-producer sequencing, but require author guidance in the same change or release as the contract, or earlier, never later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-gate-sequencing: Invert the author-guidance ordering to require guidance in the same change or release as the contract, or in an earlier change or release, never later—for example, “update author guidance in the same change or release as every new ship-blocking contract, or in an earlier change or release, never later”—and keep gate/producer sequencing on the existing “with or after, never earlier” wording.


### FINDING_2: Restore the planned Guidance structure for G-Gate-1
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-testing
- **Severity**: minor
- **Concern**: G-Gate-1 places all operational requirements in the Why sentence and omits the planned separate Guidance bullet. This diverges from the existing Why / Guidance / Deviate structure and may cause implementers to miss the same-change author-guidance, sequencing, and testing requirements. Restore a Guidance bullet while preserving any parser-visible contract text required by automated consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
