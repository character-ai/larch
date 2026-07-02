## Decision 1: "Implementer" slot scope
- **Question**: Does "implementer" (one of the 5 slot kinds to instrument) mean `review.fix_coder` only, or also /implement Step 2's feature-writing coder?
- **Resolution**: `review.fix_coder` only — the coder that applies accepted review findings, shared by /review `--fix` and /implement Step 5. /implement Step 2's separate feature-writing coder (`dispatch_step2.py`) is out of scope for this issue.
- **Source**: user

## Decision 2: Coverage breadth across skills
- **Question**: Should this change instrument /design's plan-review reviewer/voter/aggregator dispatch too, or stay limited to /review + /implement Step 5 (the only panels acceptance requires a committed example for)?
- **Resolution**: Cover all 5 slot kinds now, including /design. The shared logging helper is called at /design's dispatch sites as well; the plan must verify/wire a commit path so those rows actually reach `larch-logs/`, since today's `plan-review-slots.ndjson` is not committed at all.
- **Source**: user
