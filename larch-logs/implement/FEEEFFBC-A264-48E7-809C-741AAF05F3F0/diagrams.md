## Architecture Diagram

Architecture diagram not available.

## Code Flow Diagram

```mermaid
sequenceDiagram
    participant O as Orchestrator (Step 12)
    participant S as ship-pr.sh
    participant PF as implement-finalize.sh postmerge
    participant TD as implement-finalize.sh teardown
    participant LL as larch-log.sh
    participant Step18 as Orchestrator (Step 18)

    O->>S: run --resume-phase ci-merge
    S->>S: merge PR, advance_phase postmerge
    S->>PF: postmerge (Steps 14+15: local cleanup + verify main)
    PF-->>S: LOCAL_CLEANUP_STATUS, VERIFY_MAIN_STATUS
    S->>S: advance_phase done
    S-->>O: exit 0, PHASE=done

    Note over O,Step18: IMPLEMENT_TMPDIR still intact

    O->>Step18: continue to Step 16 to 17 to 18
    Step18->>Step18: write session-transcript.jsonl
    Step18->>TD: teardown --state-file --implement-tmpdir
    TD->>LL: manifest --field status=done --field pr_number=N
    LL-->>TD: UNCHANGED=false (manifest finalized)
    TD->>LL: commit --no-push
    LL-->>TD: flushed to git
    TD->>TD: cleanup-tmpdir.sh (removes IMPLEMENT_TMPDIR)
    TD-->>Step18: 18: cleanup status=complete
```
