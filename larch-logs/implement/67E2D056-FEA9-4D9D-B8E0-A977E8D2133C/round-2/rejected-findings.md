### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Imported heading regexes are not scanned
- **Reviewer(s)**: dyn-dyn-ast-lint-precision
- **Severity**: major
- **Concern**: Heading patterns imported from shared modules are invisible when the lint only registers locally compiled regexes, allowing fence-blind sibling parsers to evade detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-lint-precision: Also register heading patterns from imports of known shared regex symbols (or any imported name later used as the receiver of `.match`/`.search` on split lines), and add a fixture that imports `GUIDELINE_HEADING_RE` and proves it is scanned.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Additional regex extraction methods are outside detection
- **Reviewer(s)**: dyn-dyn-ast-lint-precision
- **Severity**: major
- **Concern**: The lint only inspects `.match` and `.search`, so heading extraction through `.finditer()` or `.fullmatch()` can remain fence-blind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-lint-precision: Extend detection to heading-regex `.finditer`/`.fullmatch` uses on Markdown-shaped strings (or on variables derived from `.splitlines()`), with a `learn_from_bugs`-shaped regression test.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Metadata can clear hard-trigger carriers without detection
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-ast-lint-precision
- **Severity**: major
- **Concern**: Metadata-controlled operations that empty or replace gate carriers, including `reasons = []`, `reasons.clear()`, slice deletion, or equivalent mutations, are not treated as self-disarm paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-ast-lint-precision: Treat assignments/mutations that empty or replace hard-trigger carriers (`list.clear`, `del`, reassignment to `[]`/`False`) under metadata suppression conditions as disarm paths, with fixtures for `reasons.clear()` and `reasons = []`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_16: Required unreachable-branch negative coverage is incomplete
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Tests lack loop `try`/`raise` and non-equivalent-condition negative cases needed to prevent false-positive unreachable-branch findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (0 YES)

### FINDING_17: Baseline preserves known fence-blind production parsers
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-ast-lint-precision
- **Severity**: minor
- **Concern**: The baseline explicitly grandfathered existing fence-blind parsers, so fenced headings can still be misparsed in those production paths; fixing them is follow-up parser work rather than a defect in the current lint scaffold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-ast-lint-precision: Fix parsers or shrink the baseline in dedicated follow-up.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (0 YES)

### FINDING_18: Commit-time tmpdir-pointer scanning remains unimplemented
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The I-Commit-1 commit-time mechanical scan is deferred, so run-log fields could still retain session-tmpdir pointers until a follow-up change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Implement the scan described in the invariant in a separate change.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_19: Additional full-text heading parsers are outside the lint contract
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-ast-lint-precision
- **Severity**: minor
- **Concern**: Full-text `re.findall` and `.finditer` heading parsers are not covered by the current split-line match/search lint contract, leaving pre-existing fence-blind behavior outside this change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-ast-lint-precision: Extend lint scope or fix findall-based parsers separately.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (0 YES)

### FINDING_20: Additional trusted-override regression coverage is missing
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: dyn-dyn-ast-lint-precision
- **Severity**: minor
- **Concern**: There is no regression proving that an untrusted metadata override is flagged while the trusted override paths remain compliant; this is test-gap hardening outside evidence of current production misclassification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-lint-precision: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0
