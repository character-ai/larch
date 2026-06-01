## Architecture Diagram

```mermaid
graph TD
    subgraph Activation
        DZ[design source-env.sh sourced export]
        IZ[implement session-env.sh persisted key]
        RZ[standalone review or research env-var opt-in]
    end
    DZ --> ENV[LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT in process env]
    IZ --> SENV[session-env.sh key file]
    PY[python checks.py and agents.py inherit os.environ] --> RX
    ENV --> RX[run-external-agent.sh chokepoint]
    RX --> GATE[external_launch_health_gate]
    SENV -. read-session-env-key.sh .-> GATE
    GATE --> CR[reuse check-reviewers.sh bounded probe]
    CR --> STAMP[(per-tool stamp cache 60s TTL)]
    GATE --> DEC{healthy verdict}
    DEC -- yes --> LAUNCH[launch codex or cursor full timeout]
    DEC -- no or exit 124 or 143 --> FF[fast-fail exit 7 codex or 8 cursor empty output]
    FF --> WF[existing waterfall health-class]
    WF --> CLAUDE[Claude fallback tier]
```
