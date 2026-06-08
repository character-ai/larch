### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:33-34,scripts/larch-log.sh:67-84
- **Concern**: [SCOPE-REDUCTION] Implement durable flush uses both a canonical vendor-failure-diagnostics.txt batch and a scoped *.failure-diag allowlist in round_artifact_included. Scenario: Dual paths invite double-commit or allowlist drift: the same failure could land in git twice or batch-unreachable paths miss flush when allowlist rules lag call-site changes
- **Proposed resolution**: Pick one implement durable surface: either always append redacted carrier excerpts to the batch and keep per-output *.failure-diag session-only, or commit per-output *.failure-diag only and drop the separate batch slug
