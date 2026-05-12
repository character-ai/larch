## Architecture Diagram

Architecture diagram not available.

## Code Flow Diagram

```mermaid
flowchart TD
    A[test-implement-anti-halt.sh] --> B[check_contains assertions]
    B --> B1["Step 2→3 / 4→5 / 7a→8 / 12d→14 / 14→18 reminders"]
    B --> B2["Shared SSOT — subskill-invocation.md"]
    B --> B3["Post-/bump-version boundary — SKILL.md Step 8\n(NEW: 'halt in disguise…skips sub-steps 3/3b')"]
    B --> B4["Post-/bump-version boundary — rebase-rebump-subprocedure.md\n(NEW: 'in the tool result is NOT a run-completion signal')"]
    B --> B5["Post-/design and post-/review boundaries — SKILL.md"]
    B --> B6["/design, /fix-issue, /review step-boundary checks"]
    B3 --> C{grep -Fq needle in file}
    B4 --> C
    C -->|found| D[PASS]
    C -->|missing| E[FAIL / exit 1]
```
