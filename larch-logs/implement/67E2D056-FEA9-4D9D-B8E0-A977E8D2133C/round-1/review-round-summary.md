# Review Round 1

- Mode: `diff`
- 10 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Fence guards accept non-functional or incomplete protection
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-ast-lint-precision
- **Severity**: major
- **Concern**: The markdown fence-state lint can credit unrelated booleans, helper imports, or stub helpers instead of requiring heading matches to be guarded by the actual fence-line set or a recognized fence-helper call. It may also reject compliant inline helper calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-ast-lint-precision: Extend `_uses_fence_guard` to accept `Compare` nodes whose comparator is a call to a known fence helper (module-level or locally defined names matching the fence-helper heuristic), and/or treat a `BoolOp` `and` whose left operand is such a membership test as satisfying the fence gate for the right operand’s heading match.


### FINDING_2: Nested functions can be scanned twice
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: `_nested_defs` uses `ast.walk` while `_scan_function` recursively scans nested functions, causing some nested functions to be visited twice and potentially producing duplicate identities and exit status 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_3: Suppression reasons do not identify the gate owner
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: Self-disarmable-gate suppression accepts any non-empty reason, allowing generic unaccountable suppressions even though the grammar requires owner attribution. Existing tests do not catch this.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_4: OR-shaped metadata tests can bypass size gates
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: OR-shaped conditions can skip disarm detection when the body returns `Plan`, allowing metadata-controlled paths such as `if meta.mechanical_churn or size_diff_raw: return` to bypass hard size gates while remaining lint-clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Restrict OR exemption to metadata OR-combined trigger assignments; still flag if tests with metadata when the body clears hard triggers or returns


### FINDING_5: Unconditional-return unreachable branches are missed
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The unreachable-branch scanner returns immediately after an unconditional return and does not scan following statements, so the required same-value unreachable branch case is not detected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_6: Markdown baseline integrity tests are incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Tests omit required stale-row and duplicate-row baseline failures, and lack shrink-only coverage for new live violations. A malformed or stale baseline could therefore stop failing CI and allow fence-state debt to grow silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_8: Unreachable-branch edge-case tests are incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Tests omit required `elif`-chain and unconditional-return positive cases, leaving regressions in those detection paths undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add elif-chain and unconditional-return fixtures matching the plan’s edge-case list.


### FINDING_11: Fence-skip control flow is not recognized
- **Reviewer(s)**: dyn-dyn-ast-lint-precision
- **Severity**: major
- **Concern**: The markdown lint does not recognize compliant loop structures that skip fenced lines with `continue` or `break` before a separate heading match, and therefore flags valid fence protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-lint-precision: Treat `continue`/`break` bodies guarded by a fence-membership test as establishing the same skip semantics for the rest of the loop body (or recognize `if index not in <fence-helper>(…) and <heading-match>` on one condition, including inline helper calls without a `fenced_lines` assignment).


### FINDING_12: Metadata-only early returns can be false positives
- **Reviewer(s)**: dyn-dyn-ast-lint-precision
- **Severity**: major
- **Concern**: The self-disarmable-gate detector can flag metadata validation or early-exit returns even when no hard-trigger carrier is read, cleared, or mutated, creating false positives in legitimate validation helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-lint-precision: Require evidence that the `if` body clears, replaces, or short-circuits a tracked hard-trigger name (or a variable derived from one) before emitting; treat bare metadata validation returns as non-suppression, mirroring `_is_validation_condition`.


### FINDING_14: Return proof analysis only handles first-statement returns
- **Reviewer(s)**: dyn-dyn-ast-lint-precision
- **Severity**: major
- **Concern**: `_body_returns_value` only recognizes a return when it is the first substantive statement, so conditional arms with preparation or logging before a terminal return do not contribute return proofs and later duplicate branches may be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-lint-precision: Scan each `if` body for any terminal `return` (not only single-statement bodies) before deciding whether to record `return_proofs` / `NOT(cond)` facts, or walk the body with the existing path engine instead of the first-statement shortcut.
