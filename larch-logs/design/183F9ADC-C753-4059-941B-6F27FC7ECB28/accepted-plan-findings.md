### FINDING_3: Parity test still omits reader-accepted population assertion
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The regression test can still pass even if the reader and indexer diverge on preprocessing or matcher choice, because it does not explicitly assert the reader-accepted `(id, title)` population.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: For the same fixture, derive the reader (id, title) population from parse_guideline_entries and parse_invariant_entries output and assert it equals the expected shared-constant population and coverage_index output.

