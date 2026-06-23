## Decision 1: Majority semantics
- **Question**: What does "majority of YES voters" mean exactly?
- **Resolution**: Strict majority: count of high-severity YES votes > half the count of total YES votes. With 3 YES voters: 2+ rate high → +2. With 1 YES voter: that voter must rate high → +2.
- **Source**: codebase (issue states majority; standard English majority = >50%)

## Decision 2: Rubric placement
- **Question**: Should the severity rubric appear in both code-review and plan-review voter prompts?
- **Resolution**: Yes — both paths render through `python/rendering.py`. The rubric text is added once in the rendering code that both paths use.
- **Source**: codebase (`python/rendering.py` serves both `render voter` and `render plan-review`)

## Decision 3: Prose update scope
- **Question**: Does `skills/shared/voting-protocol.md` scoring table need updating to match the new majority aggregation?
- **Resolution**: Yes — the table currently says "any YES-voter panel severity `blocker` or `major` → +2". Must be updated to "majority of YES voters rate `blocker` or `major` → +2".
- **Source**: codebase (voting-protocol.md:191)
