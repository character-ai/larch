## Architecture Diagram


```mermaid
graph TD
    subgraph Parent["/implement orchestrator"]
        D1["Step 1: post-design-boundary.sh<br/>reads design-summary.json (fixed path)"]
        D2["Step 5: /review returns<br/>reads review-summary.json (fixed path)"]
    end

    subgraph DesignHW["design heavy-worker (subagent)"]
        DW1["runs Steps 2a-3"]
        DW2["writes design-summary.json<br/>to DESIGN_TMPDIR/"]
        DW3["returns DESIGN_HEAVY=complete<br/>DESIGN_SUMMARY_FILE=<path>"]
        DW1 --> DW2 --> DW3
    end

    subgraph ReviewHW["review heavy-worker (subagent)"]
        RW1["runs Steps 1-3"]
        RW2["writes review-summary.json<br/>to REVIEW_TMPDIR/"]
        RW3["returns REVIEW_HEAVY=complete<br/>REVIEW_SUMMARY_FILE=<path>"]
        RW1 --> RW2 --> RW3
    end

    subgraph ReviewSKILL["/review SKILL.md"]
        RS1["parses REVIEW_SUMMARY_FILE<br/>from subagent return"]
        RS2["copies to parent tmpdir"]
        RS3["emits REVIEW_SUMMARY_FILE<br/>in review-result footer"]
        RS1 --> RS2 --> RS3
    end

    subgraph CAR["collect-agent-results.sh"]
        CAR1["--summary-only flag"]
        CAR2["suppresses FAILURE_REASON<br/>STRUCTURED_SIDECAR per record"]
        CAR1 --> CAR2
    end

    DesignHW --> D1
    ReviewHW --> ReviewSKILL --> D2

    style Parent fill:#e8f4f8
    style DesignHW fill:#f0e8f8
    style ReviewHW fill:#f0e8f8
    style ReviewSKILL fill:#f8f0e8
    style CAR fill:#e8f8e8
```

## Code Flow Diagram


```mermaid
sequenceDiagram
    participant Impl as /implement
    participant DesignSKILL as /design SKILL.md
    participant DesignHW as design heavy-worker
    participant ReviewSKILL as /review SKILL.md
    participant ReviewHW as review heavy-worker
    participant CAR as collect-agent-results.sh

    Impl->>DesignSKILL: invoke --subagent
    DesignSKILL->>DesignHW: Agent tool dispatch
    DesignHW->>DesignHW: write design-summary.json to DESIGN_TMPDIR
    DesignHW-->>DesignSKILL: DESIGN_HEAVY=complete\nDESIGN_SUMMARY_FILE=path
    DesignSKILL->>DesignSKILL: validate fixed path DESIGN_TMPDIR/design-summary.json\n(non-symlink, ≤2KB, jq parse, schema_version=1)
    DesignSKILL-->>Impl: manifest exported

    Impl->>ReviewSKILL: invoke --diff --subagent
    ReviewSKILL->>ReviewHW: Agent tool dispatch
    ReviewHW->>CAR: collect-agent-results.sh [--summary-only]
    CAR-->>ReviewHW: STATUS / HEALTHY per reviewer
    ReviewHW->>ReviewHW: write review-summary.json to REVIEW_TMPDIR
    ReviewHW-->>ReviewSKILL: REVIEW_HEAVY=complete\nREVIEW_SUMMARY_FILE=path
    ReviewSKILL->>ReviewSKILL: copy review-summary.json to IMPLEMENT_TMPDIR
    ReviewSKILL-->>Impl: review-result footer\nREVIEW_SUMMARY_FILE=stable-path
    Impl->>Impl: read IMPLEMENT_TMPDIR/review-summary.json\nfor code-review-tally counts
```
