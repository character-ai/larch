### FINDING_1: Adjacent-pair counting is not represented
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Structure Parity Auditor
- **Severity**: major
- **Concern**: The migration does not preserve `assert_followed_count_at_least` semantics: exact consecutive full-line pairs with minimum counts. Generic `ordered` or `contains` predicates could pass separated or insufficient matches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a dedicated predicate (for example `adjacent-pair-count-at-least`) or pin each legacy label as an explicit named design test that preserves the awk pair-count semantics and failure labels.
  - From Cursor-dyn-Structure Parity Auditor: Add an adjacent-pair predicate (exact consecutive full-line matches with a minimum count) to skill_structure_pins.py and the evaluator self-tests, and map legacy labels at scripts/test-design-structure.sh:547-551 and :679-682


### FINDING_7: Shard coverage contract conflicts with pytest conversion
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: major
- **Concern**: Retaining the seven converted targets in Bash shard prerequisites conflicts with a shard checker that excludes pytest recipes, producing orphaned prerequisites and shard coverage failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Remove these pytest targets from Bash shard prerequisites, or update the checker and its contract consistently
  - From Codex-Requirements: Remove the seven pytest targets from the Bash shard prerequisite lists, or update the shard checker and its contract to inventory them consistently


### FINDING_14: Ordered predicates must use exact full-line semantics
- **Reviewer(s)**: Cursor-dyn-Structure Parity Auditor
- **Severity**: major
- **Concern**: A substring-based ordered evaluator could pass when an early anchor appears only within a longer line, unlike the legacy exact-line checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Structure Parity Auditor: Document and implement ordered with match_mode exact-line (default for migrated design pins) versus contains, and report missing early, missing late, or reversed using line numbers


### FINDING_16: Count predicates need legacy unit and comparator fidelity
- **Reviewer(s)**: Codex-dyn-Structure Parity Auditor
- **Severity**: major
- **Concern**: The plan does not distinguish physical-line, matching-line, substring, exact, at-least, and adjacent-pair counts, so migrated checks may accept different content than the Bash harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Structure Parity Auditor: Record the legacy count unit and comparator in each pin, including physical-line, matching-line, exact, at-least, and adjacent-pair modes, with diagnostics for the observed count


### FINDING_21:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: Makefile:346,350,352;scripts/test-harness-shards-coverage.sh:69-84;docs/linting.md:147
- **Concern**: [SCOPE-REDUCTION] Pytest Make recipes cannot stay on test-harnesses shard lists. Scenario: `extract_individual_targets` drops any `test-*` recipe whose tab line contains `pytest` from the shard inventory (#5429). Replacing the seven structure targets with `python3 -m pytest ...` while keeping them on `test-harnesses-{2,4,5}` yields `orphan in shards` failures and contradicts Approach item 8 / Testing step 5.
- **Proposed resolution**: Revise Approach item 8 and `### UPDATED: Makefile` to remove the seven structure targets from `test-harnesses-2`, `test-harnesses-4`, and `test-harnesses-5` when recipes switch to pytest; keep standalone focused targets and document that contract coverage lives under `make py-test` plus the seven focused targets. Update `docs/linting.md` shard prose accordingly. Change Testing step 5 to expect shard-coverage pass after removal, not unchanged membership.


