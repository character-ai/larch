## Architecture Diagram

```mermaid
flowchart TD
  subgraph Sites["3 non-launcher Codex sites (Item B)"]
    A["review-and-fix.sh:257<br/>run_coder_dispatch codex branch"]
    B["lint-fix-loop.sh:223<br/>run_codex()"]
    C["run-negotiation-round.sh:84<br/>codex branch"]
  end

  CodexExec["codex exec --json --output-last-message --"]
  A --> CodexExec
  B --> CodexExec
  C --> CodexExec

  CodexExec -- stdout JSONL --> EV[("*.events.jsonl<br/>LOCAL ONLY")]
  CodexExec -- --output-last-message --> LG[("legacy *.log<br/>final message")]
  CodexExec -- stderr --> WL[("*.wrapper.log<br/>or *.sidecar")]

  EV --> TL["codex_launcher_record_usage_from_events"]
  TL --> TLE[("larch-tokens-*.jsonl<br/>token ledger (SANITIZED)")]

  subgraph Publication["scripts/larch-log.sh round_artifact_included"]
    PUB{"publish to<br/>committed run-logs?"}
    INCL["INCLUDE:<br/>scout-archetype-yield.tsv (Item C)<br/>findings-classification.tsv<br/>*.wrapper.log"]
    EXCL["EXCLUDE (FINDING_14):<br/>*.events.jsonl<br/>(prevent prompt/response leakage)"]
  end

  LG -.-> PUB
  WL -.-> PUB
  TLE -.-> PUB
  EV -.-> PUB
  PUB --> INCL
  PUB --> EXCL

  GIS["get-issue-state.sh:35-44<br/>(Item A: parser fix)"]
  GIS --> GISG["new value-required guard:<br/>arity AND flag-token check<br/>emits FAILED=true / ERROR / exit 1"]
```
