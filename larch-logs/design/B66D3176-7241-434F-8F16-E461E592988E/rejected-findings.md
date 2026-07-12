### [Plan Review] FINDING_4

### FINDING_4: Churn threshold is underspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The approach does not state the required cutoff for identifying churned files, so implementations could mark every touched file as churned or apply the wrong threshold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State explicitly that churned files are those touched by at least three distinct fix commits within the manifest-anchored 7-day window, and keep the existing deduplication-by-fix-commit rule.


### [Plan Review] FINDING_6

### FINDING_6: Dropped deep candidates lack durable routing reasons
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The plan requires every cap-dropped deep candidate and its routing reason to be persisted, but the existing `ledger-summary.json` contract only records bare `DEEP_TRUNCATED_ISSUES` identifiers. Stderr warnings do not provide durable audit evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the existing `ledger-summary.json` sidecar with a structured dropped-candidate list such as issue id plus promotion reason, keep `DEEP_TRUNCATED_ISSUES` stdout-compatible, and include the new field in golden/fixture coverage.


### [Plan Review] FINDING_7

### FINDING_7: Metadata-only upsert may mutate verification state
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The plan does not prevent metadata-only ledger updates from reusing the verdict upsert path. A broad merge through `_upsert_record` could rewrite stage, triage-evidence, or verdict fields and allow risk promotion to bypass the verified-triage gate for `FIXED_CLEAR` or `FIXED_LIKELY` rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a dedicated metadata merge helper that updates only coordinator analytics keys on the existing cache-key row; state explicitly in plan and tests that stages_complete, triage_evidence_verified, and verdict fields are immutable on that path.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:1329
- **Concern**: [SCOPE-REDUCTION] Chronic zones section adds churned-file detail beyond the spec. Scenario: Required design item 3 defines the churn metric, but item 8 limits the Chronic zones section to zone, bug count, and member issues. Step 6 also forces churned-file detail into that section and the golden fixture, adding report and test surface the acceptance criteria do not require.
- **Proposed resolution**: Compute churn internally for analytics if needed, but render Chronic zones with only zone, unique bug count, and member issues. Omit churned-file detail unless a follow-up issue expands the report contract.


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan step 6 / python/larch/issue/analyze_bugs.py:render_report
- **Concern**: [SCOPE-REDUCTION] Chronic zones report should omit churned-file detail. Scenario: The binding scope requires a churn metric and a Chronic zones section with zone, bug count, and member issues only. Listing churned files adds a presentation contract and golden-fixture surface that no acceptance criterion or routing rule consumes.
- **Proposed resolution**: Keep file-churn computation and unit tests in the analytics view; render Chronic zones with zone, unique bug count, and member issues only.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan.txt:33-34
- **Concern**: [SCOPE-REDUCTION] Historical git hydration and deferred ledger persistence exceed the required analytics path. Scenario: The plan adds git probes, failure handling, post-render mutations, and tests for legacy records whose absent metadata may remain unavailable under the stated compatibility contract
- **Proposed resolution**: Remove historical hydration and its persistence pass. Build analytics from metadata already present or collected by the selected-issue metadata upsert


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: plan.txt:47
- **Concern**: [SCOPE-REDUCTION] Durable per-candidate cap-drop reasons exceed the required logging contract. Scenario: The feature only requires dropped candidates to be logged instead of silently truncated. Persisting structured reasons expands ledger-summary state and tests without affecting routing or report correctness
- **Proposed resolution**: Keep the existing truncated issue identifiers and emit each issue and routing reason to stderr. Do not add a new durable reason schema

