### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: ARCHITECTURAL_GUIDELINES.md: after G-Enf-2
- **Concern**: The plan omits the required regression test that runs a producer and its fail-closed gate together. Scenario: The guideline can land without verifying the failure mode it targets. A future persisted-state gate may still ship before a writer, and markdownlint will pass because it checks only document syntax
- **Proposed resolution**: Add a concrete regression test for a representative producer and gate path, covering persisted-state availability and the gate's successful consumption of that state. Include the test file and command in the plan's files and testing strategy

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: ARCHITECTURAL_GUIDELINES.md:329
- **Concern**: G-Gate-1 Deviate-when lint and sole-file test conflict. Scenario: The plan places G-Gate-1 after G-Enf-2, whose Deviate when uses n/a, but Testing strategy requires only ARCHITECTURAL_GUIDELINES.md to change and omits python/cli.py lint guideline-no-exception. A copied n/a/never Deviate when fails make py-lint unless python/guideline-no-exception-baseline.json is updated.
- **Proposed resolution**: Add python3 python/cli.py lint guideline-no-exception to Testing strategy and require G-Gate-1 to use a substantive Deviate when clause drawn from the Edge cases (same-release migration carve-out, provably unreachable producer), not n/a or never; or add ### UPDATED: python/guideline-no-exception-baseline.json and drop the sole-file diff assertion.
