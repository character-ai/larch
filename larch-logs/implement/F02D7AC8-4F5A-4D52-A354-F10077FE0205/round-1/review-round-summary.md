# Review Round 1

- Mode: `diff`
- 7 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Preparation callback failures are not deterministic
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `prepare_corpus` is neither validated as callable nor protected against non-`ScanError` exceptions, so invalid callbacks or callback failures can produce tracebacks instead of deterministic stderr and exit code 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_4: Direct detection can leak SyntaxError
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `detect()` accesses the AST before probing syntax, allowing malformed `plan_quality.py` input to raise raw `SyntaxError` instead of the expected `ScanError`. Call `_probe_syntax(source)` before scanning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_5: Missing engine-path CLI coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Post-Piece-1 tests skip `lint.main()` and primarily call detector helpers directly. Discovery, preparation wiring, exit codes, malformed-input diagnostics, suppression rendering, and baseline-free CLI behavior can regress without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_6: `build_rule()` contract is untested
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Tests do not assert `build_rule()` fields for `syntax_policy`, `allow_inline_suppression`, `require_baseline`, and `prepare_corpus`, so rule configuration regressions could go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: Missing malformed-Python equivalence coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: The engine-path equivalence suite lacks a malformed-Python case verifying exit code 2 and the expected parse diagnostic against golden fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_8: Preparation ordering and single-call behavior are untested
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Tests do not verify that the engine calls `prepare_corpus` exactly once, before `detect`, on the correctly filtered discovered corpus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_10: Missing local `OptionalMetadata` corpus fixture
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The corpus path does not test locally defined `OptionalMetadata` in `plan_quality.py`, leaving that metadata-resolution branch unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
