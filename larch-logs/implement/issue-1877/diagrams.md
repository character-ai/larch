## Architecture Diagram

Architecture diagram not available.

## Code Flow Diagram

```mermaid
flowchart TD
    A[Skill invocation\nwith optional --run-id ID] --> B{--run-id present?}
    B -- Yes --> C[Parse: run_id = ID\nStrip from ARGUMENTS]
    B -- No --> D[run_id = auto-generate\nno change to ARGUMENTS]
    C --> E[Skill execution\nwith stripped ARGUMENTS]
    D --> E
    E --> F{Script-backed\nskill?}
    F -- Yes --> G[Invoke script\nwith stripped ARGUMENTS\nnot passing --run-id]
    F -- No --> H[Orchestrator-driven\nsteps use run_id\nfor session identity]
    G --> I[Script output]
    H --> I
    I --> J[Result returned to caller]
```
