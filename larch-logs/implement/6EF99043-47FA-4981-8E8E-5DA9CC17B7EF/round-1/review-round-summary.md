# Review Round 1

- Mode: `diff`
- 7 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Missing targets can make absent pins pass
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `absent` pins return successfully when their target file is missing, allowing deleted or misspelled targets to satisfy the contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Remove the early return and require `full.is_file()` before evaluating every predicate, with a negative self-test for a missing `absent` target.
  - From cursor-specialist-edge-cases: Fail on missing files for absent unless the path is explicitly must-not-exist; or require a contains pin on the same path.
  - From codex-specialist-edge-cases: Require a regular target file for every predicate and test missing absent targets.


### FINDING_2: Legacy assertion labels lack one-to-one test coverage
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The legacy-label inventory does not prove that every legacy assertion, including the missing bug no-flags assertion, maps to exactly one collected pytest node or named test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add an explicit inventory and assert every legacy label maps to exactly one param_id or named test
  - From codex-specialist-correctness: Restore the negative assertion and label, then make `python/tests/skills/test_skill_structure.py:284-294` validate against an independent complete legacy-label inventory.
  - From cursor-specialist-edge-cases: Build expected labels from pins plus LEGACY_LABELS; assert bijection against collected pytest node IDs and specialized failure strings.
  - From codex-specialist-edge-cases: Validate unique label-to-node mappings and focused-selection membership.
  - From cursor-specialist-testing: Crosswalk pin labels and LEGACY_LABELS to parameter IDs or named tests; require exactly one owner per legacy label.
  - From codex-specialist-testing: Declare and validate per-label node mappings, preserve legacy labels, and validate focused selections against mapped nodes.


### FINDING_3: Focused selections are not checked for complete coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Focused Makefile `-k` expressions are only checked for existence, so pins or specialized tests can be omitted from focused structure runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Collect node IDs and assert each is selected by FOCUSED_SELECTION[skill]
  - From cursor-specialist-edge-cases: Collect pytest nodes per skill and assert each matches FOCUSED_SELECTION and none are orphaned.
  - From codex-specialist-edge-cases: Validate unique label-to-node mappings and focused-selection membership.
  - From cursor-specialist-testing: Programmatically match collected pytest node IDs against each skill's FOCUSED_SELECTION -k expression; fail on any uncovered pin or specialized test.
  - From codex-specialist-testing: Declare and validate per-label node mappings, preserve legacy labels, and validate focused selections against mapped nodes.


### FINDING_4: cross_file_bound has invalid proximity semantics
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: `cross_file_bound` compares line numbers from unrelated files, so its bound does not represent meaningful proximity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Remove the predicate or match legacy same-file character-window semantics
  - From cursor-specialist-edge-cases: Remove or fix the predicate and add positive/negative self-tests per plan.
  - From cursor-specialist-testing: Add tmp_path positive/negative self-tests for each missing predicate and match mode.


### FINDING_8: `count_at_least` defaults to exact comparison
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: `count_at_least` uses exact comparison when `comparator` is omitted, so multiple matches fail a predicate that should accept at least the expected count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Derive comparison from the predicate kind or require and validate a compatible explicit comparator.


### FINDING_11: Invalid pin modes and bounds are accepted
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Pin validation does not reject invalid enum-like values or numeric bounds, allowing malformed pins to weaken or bypass checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Validate all enum-like fields and bounds; add positive and negative tests for every predicate, mode, unit, and comparator.


### FINDING_12: Checker self-tests omit evaluator branches
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: Self-tests do not cover several predicate and match-mode branches, including `cross_file_bound`, regex matching, substring counts, and ordered contains pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add tmp_path positive/negative self-tests for each missing predicate and match mode.
  - From codex-specialist-testing: Validate all enum-like fields and bounds; add positive and negative tests for every predicate, mode, unit, and comparator.
