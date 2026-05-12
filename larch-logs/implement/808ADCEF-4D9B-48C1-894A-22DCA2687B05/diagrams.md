## Architecture Diagram

Architecture diagram not available.

## Code Flow Diagram

## Code Flow Diagram

```mermaid
sequenceDiagram
    participant O as /implement orchestrator
    participant S as ship-pr.sh
    participant F as implement-finalize.sh
    participant L as larch-log.sh

    Note over O,L: Pre-bump log flush (Step 7a tail — existing)
    O->>L: commit --no-push (token-report, timing-report)
    L-->>O: COMMIT_SHA=<sha>

    Note over O,L: Bug 1 fix: ci-merge flush
    O->>S: --resume-phase ci-merge
    S->>S: run_ci_phase(ci-merge)
    S->>L: commit --skill implement --run-id <RUN_ID>
    Note right of L: flushes version-bump-reasoning,<br/>oos-issues, execution-issues, etc.
    L-->>S: pushed to remote branch
    S->>S: ci-wait.sh → ACTION=merge
    S->>S: merge-pr.sh

    Note over F,L: Bug 2 fix: teardown safety-net flush
    O->>F: teardown
    F->>L: commit --run-id <RUN_ID> --no-push
    Note right of L: handles stalled runs where<br/>ci-merge flush never ran
    L-->>F: ok or no-op

    Note over F,L: Bug 3 fix: correct run_id in write_version_reasoning_fragment
    O->>F: postbump
    F->>F: write_version_reasoning_fragment()
    Note right of F: run_id = LARCH_RUN_ID<br/>  or RUN_ID (env)<br/>  or read_state RUN_ID ← NEW<br/>  or basename suffix (last resort)
    F->>L: write --run-id <correct-RUN_ID> --batch version-bump-reasoning
    L-->>F: written to larch-logs/implement/<RUN_ID>/

    Note over S,F: Bug 3 enabler: RUN_ID in state files
    S->>F: postbump-state.sh (now includes RUN_ID=...)
    S->>F: finalize-state.sh (now includes RUN_ID=...)
```
