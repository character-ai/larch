### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:6-73
- **Concern**: [SCOPE-REDUCTION] Plan still removes the hardcoded SKILL matrix and expands plan-review.md reconcile while binding scope requires leaving the matrix in loaded SKILL prose.. Scenario: Round 3 added Contract-tail replacement, static-slugs enumeration, Consumer/When-to-load/Contract parity greps, and failure-mode checks on top of SKILL stripping. Binding OOS scope records registry dispatch made SKILL duplication optional and rejected dedup as in-scope churn. Implementing this plan ships the opposite plus extra two-file doc churn.
- **Proposed resolution**: Re-scope or close the leave-matrix tracking issue first. Minimum-change path per binding scope: no-op (leave skills/design/SKILL.md matrix prose unchanged; skip plan-review.md topology reconcile).
