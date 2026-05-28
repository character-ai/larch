## Decision 1: Gap 2 expected outcome
- **Question**: Should the all-OOS input + attestation-only aggregate output test assert acceptance or rejection?
- **Resolution**: Accept (REASON=ok). Encode current behavior as a regression sentinel; do not modify aggregate-findings.sh.
- **Source**: user

## Decision 2: Test surface scope
- **Question**: Which file(s) get edited?
- **Resolution**: skills/review/scripts/test-aggregate-findings.sh only. No changes to skills/review/scripts/aggregate-findings.sh (issue is test-only).
- **Source**: codebase (per OOS issue body)
