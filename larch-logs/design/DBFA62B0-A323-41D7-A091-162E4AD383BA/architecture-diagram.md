## Architecture Diagram

```mermaid
graph TD
    A[review-core.sh] -->|--panel<br/>--launched-slots<br/>--round-num| B[check-reviewer-failure-threshold.sh]
    C[collector results file] --> B
    B -->|STATIC_INTENDED_SLOTS = 6| D[FAILED_SLOTS calc]
    D -->|HALF_PLUS_ONE_MIN = 4| E[THRESHOLD_OK]
    E --> F[review-core.sh: panel-failed or continue]

    G[dispatch-panel.sh] -.->|launches 6 Cursor slots only| H[panel manifest]
    H -.->|STATIC_SLOT_COUNT=6| A

    style B fill:#9f9
    style D fill:#9f9
```

Before the fix, B used a round-aware `STATIC_INTENDED_SLOTS` (12 for HARD round-1, 7 for SIMPLE round-1, 6 otherwise) that did not match the post-#2449 launcher manifest of always 6 Cursor slots. After the fix, B uses a flat 6 in all cases so `NEVER_LAUNCHED = INTENDED − LAUNCHED` no longer adds phantom failures.
