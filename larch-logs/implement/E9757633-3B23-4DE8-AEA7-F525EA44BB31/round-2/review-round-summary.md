# Review Round 2

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: non-UTF-8 source reads crash `lint_guidelines_note_wrapper_bypass`
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: `scan_file()` still only handles `OSError` when reading source text, so non-UTF-8 `python/larch/**/*.py` files can raise `UnicodeDecodeError` and crash the lint instead of failing closed with the planned exit-2 diagnostic; this also needs the corresponding non-UTF-8 regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.


