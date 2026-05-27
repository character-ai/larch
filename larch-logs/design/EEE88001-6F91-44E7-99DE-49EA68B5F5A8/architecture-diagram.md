## Architecture Diagram

```mermaid
flowchart TD
    A[review-core.sh collect_findings] --> B{findings_count == 0?}
    B -- yes --> Z[emit_zero_findings_branch shared function]
    B -- no --> C[aggregate-findings.sh]
    C --> D{aggregate_reason}
    D -- validation-exhausted --> E[agg-exhaust branch existing]
    D -- ok --> F{MERGED_COUNT raw value}
    F -- absent or non-zero --> G[dispatch-code-voters.sh launch 3 voters]
    F -- equals literal 0 NEW --> Z
    G --> H[tally-code-votes.sh]
    Z --> H
    H --> I[emit-tally.sh]
    I --> J[REVIEW_CORE_STATUS=zero-findings OR REVIEW_CORE_STATUS=ok]

    style Z fill:#cfc,stroke:#080
    style F fill:#cfc,stroke:#080
```

The shared `emit_zero_findings_branch` function is the structural change: it is extracted from the existing inlined zero-findings body (lines 453-514) and called from both the pre-aggregator zero-findings site and the new post-aggregator empty-merge site. Both call sites emit `REVIEW_CORE_STATUS=zero-findings` so downstream wrappers (review-and-fix, /implement Step 5) see a single terminal status for both no-findings cases.
