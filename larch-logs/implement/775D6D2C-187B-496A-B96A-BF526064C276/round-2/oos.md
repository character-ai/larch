### FINDING_7: [OUT_OF_SCOPE] Explicit `--search` does not bind `RESOLVED_SEARCH`
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The explicit `--search` path can leave `RESOLVED_SEARCH` empty, causing an empty `--search` argument to be passed and allowing preparation or mining to fall back to the default query.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Bind RESOLVED_SEARCH in Step 1 for the explicit --search branch; pre-existing


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Preparation failures are not gated before KV parsing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Step 2 may continue to parse output after preparation fails, potentially mishandling digest and origin-path values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Check prepare rc and abort before reading DIGEST_PATH or ORIGIN_HEADLINE_PATH.
  - From cursor-specialist-edge-cases: Check prepare rc and abort before reading DIGEST_PATH or ORIGIN_HEADLINE_PATH.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Origin classification scans fenced code
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-origin-allowlist
- **Severity**: minor
- **Concern**: Origin classification scans full root-cause bodies without removing fenced code, so illustrative markers or regression language inside code samples can create false classifications and skew chains or ratios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Strip fenced spans from origin sources; heuristic precision tradeoff
  - From dyn-dyn-origin-allowlist: Reuse `_fenced_line_indices` (or an equivalent helper) to remove fenced line ranges from each origin source string before referenced-marker, bare-regression, and heuristic scans; add a fixture with a marker only inside a fenced block and assert `unknown` (or no false chain).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Digest-size accounting lacks dedicated multi-record coverage
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Multi-issue digest-size accounting is not separately tested, leaving newline-separator under-counting undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Compute DIGEST_CHARS from the exact digest.jsonl bytes on disk.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Singular suggested-fix heading lacks negative allowlist coverage
- **Reviewer(s)**: dyn-dyn-origin-allowlist
- **Severity**: minor
- **Concern**: Negative allowlist coverage exists for `## Suggested fix(es)` but not for the singular `## Suggested fix` heading listed in `WANT_SECTIONS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-origin-allowlist: behavior should match, but the singular variant is not regression-tested.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Bare regression detection has no dedicated precision tests
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-origin-allowlist
- **Severity**: minor
- **Concern**: Negated and test-context uses of “regression” can inflate origin statistics, but the precision behavior is not fully covered by dedicated fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Narrow the bare-regression pattern if precision becomes a requirement later.
  - From cursor-specialist-testing: Narrow bare-regression detection with negative lookbehind or required residual context.
  - From dyn-dyn-origin-allowlist: Narrow bare-regression detection with negative lookbehind/ahead or an allowlisted phrase set (for example require `bare regression`, `a regression`, or `regressed`), and add pytest cases for the negated and test-context strings so the ratio stays faithful to residual language.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Prose-only validation lacks cluster-boundary coverage
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-origin-allowlist
- **Severity**: minor
- **Concern**: An adjacent-cluster negative test is missing for the broad-window prose-only validator, so borrowing citations or mechanical wording from neighboring clusters is not regression-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Parse cluster or proposal blocks and validate each marker within its own block; add adjacent-cluster negative fixture.
  - From dyn-dyn-origin-allowlist: `_validate_prose_only_markers` validates citations and mechanical-alternative text in a fixed ±400/800 character window instead of the containing cluster or proposal block. A malformed marked cluster can pass by borrowing `#6746`, `#6747`, and an incidental `lint`/`hook` mention from a neighboring cluster.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_17: [OUT_OF_SCOPE] `validate_report_main` lacks CLI integration tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Registry and argument-wiring regressions for the Step 4 report gate are only exposed at skill runtime because `validate_report_main` lacks direct CLI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add pytest coverage for success KV, contract-failure exit 2, and missing file paths.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
