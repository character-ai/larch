### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:425-435,858-872
- **Concern**: [SCOPE-REDUCTION] Structured sidecar failure handling is broader than the no-findings rescue the feature needs. Scenario: The plan removes collector structured validation, then keeps any OK reviewer as zero parsed rows when lazy structured generation returns non-zero. A malformed structured TSV that still passes substantive validation by length and provenance would stop being NOT_SUBSTANTIVE and could make real findings disappear as a clean zero-findings round.
- **Proposed resolution**: Limit the zero-row fallback to recognized no-findings prose or sentinel outputs. For structured-looking output or other sidecar generation failures, keep a degraded or failed record equivalent to the current structured-validation failure path.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:859-868
- **Concern**: [SCOPE-REDUCTION] Structured sidecar failures are fail-open for every OK reviewer, not just prose no-findings. Scenario: A reviewer emits a prose finding or malformed structured row that passes substantive validation but cannot materialize a structured sidecar; the plan records OK with zero parsed rows, so the round can finish as zero-findings and drop a real review failure
- **Proposed resolution**: Narrow the fail-open branch to outputs that match the no-findings prose or sentinel case; keep existing NOT_SUBSTANTIVE or failed handling for structured-looking outputs or finding prose when sidecar generation fails
