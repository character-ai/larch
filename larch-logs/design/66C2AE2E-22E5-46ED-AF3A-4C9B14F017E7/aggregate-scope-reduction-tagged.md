### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/skills/skill_structure_pins.py:1
- **Concern**: [SCOPE-REDUCTION] `bounded cross-file` predicate has no legacy consumer. Scenario: None of the seven Bash structure harnesses implement a bounded cross-file assertion; shipping an unused predicate adds evaluator and self-test surface without parity benefit
- **Proposed resolution**: Drop `bounded cross-file` from Approach item 3, pin kinds, and self-tests unless a concrete legacy label is identified first

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: docs/linting.md:404
- **Concern**: [SCOPE-REDUCTION] Plan over-requires seven focused-target documentation rows. Scenario: Only make test-alias-structure has a dedicated docs/linting.md table row today (line 404); the other six structure targets are Makefile-only. Requiring seven new rows expands doc churn without changing lint behavior once shard lists move to pytest.
- **Proposed resolution**: Revise the single existing alias row plus shard-coverage prose to describe the shared pytest suite and per-skill -k selections; do not invent six redundant table entries.

### FINDING_24:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: docs/linting.md:404
- **Concern**: [SCOPE-REDUCTION] Plan overstates seven linting.md target rows when only alias is documented. Scenario: docs/linting.md currently documents only make test-alias-structure; the other six focused structure targets have no table rows. Requiring seven row updates invites six redundant doc additions without improving migration verification.
- **Proposed resolution**: Revise the docs/linting.md task to update the existing alias row plus shard-coverage prose, and only add new rows if a target already has a dedicated entry today.
