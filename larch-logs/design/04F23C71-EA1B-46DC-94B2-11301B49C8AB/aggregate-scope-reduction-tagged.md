### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:187-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice compose_pr_body regression duplicates existing placement coverage. Scenario: test_pr_body.py already asserts architectural_guidelines_note renders under ## Architectural guidelines and precedes ## Code Flow Diagram (lines 1125-1128). Adding another compose test for static drop text adds churn without guarding a new failure mode.
- **Proposed resolution**: Drop the planned test_pr_body.py addition; rely on ship and final_report tests that assert the actual drop-notice string end-to-end.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:185-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice `compose_pr_body` regression duplicates existing architectural-guidelines placement coverage. Scenario: `test_compose_pr_body_includes_guideline_note_before_mermaid` already asserts any non-empty `architectural_guidelines_note` lands under `## Architectural guidelines` before the Mermaid section; a second test differing only in static drop-notice wording adds churn without new contract signal
- **Proposed resolution**: Drop the `### UPDATED: python/test_pr_body.py` bullet; keep existing placement and redaction tests unchanged

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:185-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice `compose_pr_body` test duplicates existing placement coverage. Scenario: `python/test_pr_body.py:1117-1128` already asserts a non-empty `architectural_guidelines_note` renders under `## Architectural guidelines` with ordering vs `## Code Flow Diagram`. A second test that passes the static drop-notice string exercises the same compose path and adds churn without new failure detection.
- **Proposed resolution**: Skip the `test_pr_body.py` addition unless `compose_pr_body` changes; rely on `test_ship.py` and `test_final_report.py` integration coverage for drop-notice delivery.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:185-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice `compose_pr_body` regression duplicates existing guideline placement coverage. Scenario: `test_compose_pr_body_includes_guideline_note_before_mermaid` (lines 1121-1128) already asserts arbitrary `architectural_guidelines_note` text is rendered under `## Architectural guidelines` before Mermaid. A second test differing only by the static drop-notice string adds no new contract signal for this bugfix.
- **Proposed resolution**: Drop the planned `test_pr_body.py` addition; rely on existing placement/redaction tests plus ship/final_report integration coverage.
