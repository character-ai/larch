### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:1329
- **Concern**: [SCOPE-REDUCTION] Chronic zones section adds churned-file detail beyond the spec. Scenario: Required design item 3 defines the churn metric, but item 8 limits the Chronic zones section to zone, bug count, and member issues. Step 6 also forces churned-file detail into that section and the golden fixture, adding report and test surface the acceptance criteria do not require.
- **Proposed resolution**: Compute churn internally for analytics if needed, but render Chronic zones with only zone, unique bug count, and member issues. Omit churned-file detail unless a follow-up issue expands the report contract.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan step 6 / python/larch/issue/analyze_bugs.py:render_report
- **Concern**: [SCOPE-REDUCTION] Chronic zones report should omit churned-file detail. Scenario: The binding scope requires a churn metric and a Chronic zones section with zone, bug count, and member issues only. Listing churned files adds a presentation contract and golden-fixture surface that no acceptance criterion or routing rule consumes.
- **Proposed resolution**: Keep file-churn computation and unit tests in the analytics view; render Chronic zones with zone, unique bug count, and member issues only.

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan.txt:33-34
- **Concern**: [SCOPE-REDUCTION] Historical git hydration and deferred ledger persistence exceed the required analytics path. Scenario: The plan adds git probes, failure handling, post-render mutations, and tests for legacy records whose absent metadata may remain unavailable under the stated compatibility contract
- **Proposed resolution**: Remove historical hydration and its persistence pass. Build analytics from metadata already present or collected by the selected-issue metadata upsert

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: plan.txt:47
- **Concern**: [SCOPE-REDUCTION] Durable per-candidate cap-drop reasons exceed the required logging contract. Scenario: The feature only requires dropped candidates to be logged instead of silently truncated. Persisting structured reasons expands ledger-summary state and tests without affecting routing or report correctness
- **Proposed resolution**: Keep the existing truncated issue identifiers and emit each issue and routing reason to stderr. Do not add a new durable reason schema
