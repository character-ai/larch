### [Plan Review] FINDING_4

### FINDING_4: Stale-note cleanup can be skipped by earlier fallback branches
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The stale-note cleanup branch can be skipped when an earlier staged-present or marker-return fallback runs first. If a failed pin hits a stale durable note while `staged_present` is true, or `final_report` sees a pre-existing drop marker while stale durable artifacts still exist, the plan can return the notice before `invalidate_implement_note` runs. That leaves old guideline files on disk and makes drop-notice behavior depend on branch order instead of one ordered cleanup path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the stale-note branch take precedence over the staged-only or marker-return fallback in both helpers, or merge them into one ordered decision tree that persists the notice, invalidates once, then returns.


### [Plan Review] FINDING_6

### FINDING_6: Final-report live drop paths omit `head_sha` guard
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Planned live drop-notice paths in `_architectural_guidelines_section` omit a `head_sha` guard while ship already returns early when `head_sha` is empty. The plan gates drop emission in `_pin_and_load_guidelines_note` on non-empty `head_sha` (edge case line 192) but still lets final-report live branches persist and return a HEAD-drift notice when `_current_head_sha()` is empty yet staged artifacts remain. That revives round-1 FINDING_3: operators can see a drift explanation when HEAD is unknown instead of the current empty result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Before any live persist/return branch (lines 100-105), require non-empty `head_sha`; keep the early `read_dropped_note_notice` path so a ship-persisted artifact can still render when HEAD cannot be resolved.


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:187-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice compose_pr_body regression duplicates existing placement coverage. Scenario: test_pr_body.py already asserts architectural_guidelines_note renders under ## Architectural guidelines and precedes ## Code Flow Diagram (lines 1125-1128). Adding another compose test for static drop text adds churn without guarding a new failure mode.
- **Proposed resolution**: Drop the planned test_pr_body.py addition; rely on ship and final_report tests that assert the actual drop-notice string end-to-end.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:185-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice `compose_pr_body` regression duplicates existing architectural-guidelines placement coverage. Scenario: `test_compose_pr_body_includes_guideline_note_before_mermaid` already asserts any non-empty `architectural_guidelines_note` lands under `## Architectural guidelines` before the Mermaid section; a second test differing only in static drop-notice wording adds churn without new contract signal
- **Proposed resolution**: Drop the `### UPDATED: python/test_pr_body.py` bullet; keep existing placement and redaction tests unchanged


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:185-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice `compose_pr_body` test duplicates existing placement coverage. Scenario: `python/test_pr_body.py:1117-1128` already asserts a non-empty `architectural_guidelines_note` renders under `## Architectural guidelines` with ordering vs `## Code Flow Diagram`. A second test that passes the static drop-notice string exercises the same compose path and adds churn without new failure detection.
- **Proposed resolution**: Skip the `test_pr_body.py` addition unless `compose_pr_body` changes; rely on `test_ship.py` and `test_final_report.py` integration coverage for drop-notice delivery.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:185-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice `compose_pr_body` regression duplicates existing guideline placement coverage. Scenario: `test_compose_pr_body_includes_guideline_note_before_mermaid` (lines 1121-1128) already asserts arbitrary `architectural_guidelines_note` text is rendered under `## Architectural guidelines` before Mermaid. A second test differing only by the static drop-notice string adds no new contract signal for this bugfix.
- **Proposed resolution**: Drop the planned `test_pr_body.py` addition; rely on existing placement/redaction tests plus ship/final_report integration coverage.


