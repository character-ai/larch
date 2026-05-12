## Architecture Diagram

Architecture diagram not available.

## Code Flow Diagram

```mermaid
sequenceDiagram
    participant SKILL as SKILL.md Step 5.1
    participant GBC as gather-branch-context.sh
    participant LR as launch-review.sh
    participant RSP as render-specialist-prompt.sh

    SKILL->>GBC: --output-dir $TMPDIR
    GBC->>GBC: git log MERGE_BASE..HEAD --oneline > commit-log.txt
    GBC->>GBC: COMMIT_COUNT=$(wc -l < commit-log.txt)
    GBC-->>SKILL: COMMIT_COUNT=N
    SKILL->>LR: --agent-file reviewer-X.md --commit-count N
    LR->>LR: RENDER_ARGS += --commit-count N
    LR->>LR: sentinel: printf COMMIT_COUNT=N
    LR->>RSP: --agent-file --mode diff --commit-count N
    alt 1 <= N <= 5
        RSP-->>LR: prompt omits git log instruction
    else N > 5 or empty
        RSP-->>LR: prompt includes git log instruction
    end
```
