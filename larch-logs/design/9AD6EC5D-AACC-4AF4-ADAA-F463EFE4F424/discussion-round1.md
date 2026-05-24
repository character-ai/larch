## Decision 1: Scope — which plan-revision paths get the dedup sweep
- **Question**: Should the duplicate-content sweep apply to all plan-revision paths or strictly Gate B Apply only?
- **Resolution**: Gate B Apply only (the Apply-all / per-finding Apply step in approval-gates.md). The Step 1e Gate A "Discuss more" sub-round that MAY revise plan.txt is explicitly OUT of scope. Step 2b initial plan write is OUT of scope (no voted-in findings to apply yet).
- **Source**: user

## Decision 2: Match rule — how to detect a duplicate
- **Question**: How should "duplicate line" be defined — exact-match, whitespace-normalized, block-level, or LLM-judgment?
- **Resolution**: Use the agent's reasoning (LLM judgment) rather than deterministic pattern matching. The agent that updates the plan should identify semantically duplicated content, not just byte-identical lines.
- **Source**: user
