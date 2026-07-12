## Decision 1: Waterfall lane order and primary lane
- **Question**: Should Cursor/Composer-2.5 become the new primary assessment lane (run first on every assessment), or keep Claude/Sonnet primary with Cursor then Codex as failure-only fallbacks?
- **Resolution**: Cursor/Composer-2.5 is the new primary lane. The full waterfall order for every architectural assessment is Cursor/Composer-2.5 -> Codex/Terra -> Claude/Sonnet-4-6. Claude/Sonnet-4-6 is the last-resort lane. This changes steady-state behavior: assessments now run on Cursor first, not only on failure.
- **Source**: user

## Decision 2: Per-lane attempt budget
- **Question**: How many attempts per lane before advancing to the next lane, to keep Step 8 bounded?
- **Resolution**: One attempt per lane. On empty stdout, unparseable JSON, timeout, or non-zero exit, advance immediately to the next lane. Total is at most 3 lane attempts per kind. Only after the last lane (Claude/Sonnet-4-6) is exhausted does the assessment emit `unavailable` and route to operator-bail.
- **Source**: user

## Decision 3: Waterfall trigger scope (from issue, not re-asked)
- **Question**: When does the waterfall trigger, and when does it stop?
- **Resolution**: The waterfall triggers only on the "unavailable" failure mode: empty stdout, unparseable JSON, timeout, or non-zero exit that currently yields `unavailable`. It does NOT trigger when a lane produces a real assessment that reports a violation or a genuine `dropped` result; those stop the waterfall and are returned as-is. Invariant-violation and genuine `dropped` semantics stay unchanged. The waterfall applies per-kind: invariants and guidelines advance independently, each stopping at the first lane that yields a parseable assessment. Preserve the #7057 sanitized diagnostic detail so the final operator-bail handoff still reports the last lane's failure detail.
- **Source**: codebase (issue #7097 root cause and suggested fix #5)

## Decision 4: Reuse existing tool machinery (from issue, not re-asked)
- **Question**: Build a new tool-selection path or reuse existing machinery?
- **Resolution**: Reuse the existing tool availability and launch machinery used by the implementer dispatcher and the Step 8 CI-fixer (Codex and Cursor launchers) rather than adding a parallel tool-selection path. If a lane's tool binary is unavailable, treat that lane as skipped and advance to the next lane (not a hard failure).
- **Source**: codebase (issue #7097 suggested fix #4)
