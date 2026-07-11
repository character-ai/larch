# Review Round 2

- Mode: `diff`
- 12 accepted, 6 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Enumerated split-line loops evade Markdown fence checks
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-ast-lint-precision
- **Severity**: major
- **Concern**: The scanner does not recognize common `enumerate(text.splitlines())` or `enumerate(split_var)` loops as split-line iteration, so heading matches over the enumerated line variable can evade fence-state validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-ast-lint-precision: Treat `enumerate(<splitlines…>)` and `enumerate(<name in split_vars>)` as split-line iterators (or always propagate tuple targets from any `enumerate` loop over line-oriented text), and add a regression test with `enumerate(raw_text.splitlines())` that must fail without fence gating.


### FINDING_2: Fence membership checks are not tied to the active line
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The lint credits arbitrary fence-set membership checks without proving that the compared value represents the current loop index or line, allowing unrelated checks such as `if 0 not in fenced_lines` to suppress a real violation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_3: Boolean fence-state locals are not recognized as guards
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Boolean locals derived from fence membership, such as `in_fence = idx in fenced_lines`, are not connected to later heading-match guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_4: Subscripted line expressions evade heading-match detection
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Heading matches applied to tracked split-line values through subscripts such as `lines[index]` are not recognized, allowing fence-blind parsers to pass the lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_5: Fence-helper discovery accepts unverified helpers
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Any imported or defined helper with a fence-related name can be treated as evidence of fence protection, even when it returns an empty or unrelated set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_6: Function-local fence helpers are not tracked
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-ast-lint-precision
- **Severity**: major
- **Concern**: Fence-helper imports and fence-set assignments inside function bodies are not credited, causing compliant parsers that use a local shared helper to be flagged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-ast-lint-precision: Track fence-helper imports and fence-set assignments inside function bodies (same as top-level `_track_assignment`), or treat any call to a `*fence*` helper as a fence source when gating loop iteration.


### FINDING_9: Required Markdown-lint regression coverage is incomplete
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: The test suite lacks the required imported-helper misplaced-suppression and unreadable-source cases, leaving valid helper usage and source-read failure behavior insufficiently protected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_11: Nested metadata branches evade self-disarm detection
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The scanner does not recurse into nested control-flow bodies, so a metadata-controlled early return nested inside another branch can suppress a hard trigger without producing a finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_12: Inline size computations are not treated as hard-trigger context
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Metadata OR-guards that combine metadata conditions with inline size comparisons or `diff_lines`/plan-size computations can evade detection when no pre-named hard-trigger binding exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Treat inline plan-size threshold comparisons and `diff_lines`/`plan_lines` parameters as hard-trigger context in OR/early-return detection; add a regression test for that shape.


### FINDING_13: Hard-trigger bindings are collected without execution order
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Precomputing hard-trigger names from all assignments can falsely classify a metadata early return that occurs before the trigger is assigned as a disarm of that trigger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_14: Required self-disarmable-gate regression coverage is incomplete
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Tests do not cover metadata-resolution scope, malformed source, deterministic diagnostics, direct-definition imports, or ordered live-violation CLI behavior required to protect I-Gate-1 enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_15: Exhaustive returning chains hide unreachable tail code
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: When an exhaustive `if`/`else` chain returns on every branch, the scanner loses terminal-return state and fails to inspect later straight-line code that is unreachable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
