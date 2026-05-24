## Architecture Diagram

```mermaid
graph TD
  subgraph design_orch[/design SKILL.md]
    A0[Step 0a session-setup]
    A1[Step 0b clarify exit]
    A2[Step 0b already-planned cancel]
    A3[Step 0b tier-gate cancel]
    A4[Step 1c/1d sprawl cancel]
    A5[Step 2b.5 hard cancel]
    A6[Step 5 happy finalize]
    A7[Step 5c failed-plan-write]
    A8[Step 2b.5 Split-path exclusion]
  end

  subgraph implement_orch[/implement SKILL.md]
    B1[Step 17 write-final-report --print-stdout]
    B2[Step 18 write-final-report silent refresh]
    B3[Step 18 chat-tail DELETED]
  end

  subgraph helpers[Shared helpers]
    H1[render-final-summary.sh NEW]
    H2[render-run-summary.sh extended skill design]
    H3[token-cost.sh + lib-cost-line-format.sh]
    H4[token-report.sh strip dollar add Tokens]
    H5[timing-report.sh]
    H6[tracking-issue-summary.sh]
    H7[design-log-publish.sh]
    H8[render-cost-line.sh DEPRECATED standalone]
  end

  subgraph artifacts[Outputs]
    O1[DESIGN_TMPDIR/final-summary.md]
    O2[larch-logs/design/RUN_ID/final-summary.md]
    O3[GitHub comment marker larch:final-summary v1 runid R]
    O4[Chat rendered summary block]
  end

  A1 --> H1
  A2 --> H1
  A3 --> H1
  A4 --> H1
  A5 --> H1
  A6 --> H1
  A7 --> H1
  A8 -.->|skip render, preserve DESIGN_TMPDIR| O1

  H1 -->|Phase 1 pre-publish, file only| H2
  H1 -->|token JSON| H4
  H1 -->|timing JSON| H5
  H2 --> H3
  H1 -->|Phase 2 post-publish| H6

  A6 -->|happy path only| H7
  H1 -->|Phase 1 writes| O1
  H7 -->|commits Phase 1 file| O2
  H1 -->|Phase 2 prints| O4
  H6 -->|upsert when ISSUE_NUMBER non-empty| O3

  B1 --> H2
  B2 -->|silent, no --print-stdout| H6

  H8 -.->|no in-tree callers, harness only| H8

  classDef new fill:#cfe2ff,stroke:#0d6efd,color:#000
  classDef updated fill:#fff3cd,stroke:#ffc107,color:#000
  classDef deleted fill:#f8d7da,stroke:#dc3545,color:#000
  classDef artifact fill:#d1e7dd,stroke:#198754,color:#000
  class H1 new
  class H2,H4,B1,B2 updated
  class B3 deleted
  class H8 deleted
  class O1,O2,O3,O4 artifact
```
