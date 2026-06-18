## Decision 1: JSONL findings population scope
- **Question**: Should `review-findings-full.jsonl` contain real JSONL finding entries for self-review runs?
- **Resolution**: Tally-only fix. `review-findings-full.jsonl` stays as an empty sentinel. Only scalar counts (`accepted_count`, `rejected_count`) in `code-review-tally.json` need fixing.
- **Source**: user

## Decision 2: Blocking dependency (#4617)
- **Question**: Is this fix blocked by #4617 (multi-round tally flush fix, same file `python/review_and_fix.py`)?
- **Resolution**: Not blocked. #4617 has landed (commit `e3c0497bb`). No rebase needed.
- **Source**: codebase

## Decision 3: Python `write_self_review_tally` changes
- **Question**: Does `python/review_and_fix.py` need changes?
- **Resolution**: No structural Python changes needed. The function already correctly accepts `--accepted` and `--rejected` and forwards them to `voting write-tally`. The fix is in the SKILL.md fence that calls the function with hardcoded zeros.
- **Source**: codebase

## Decision 4: Accepted count tracking mechanism
- **Question**: How does the SKILL.md orchestration track how many inline fixes were applied?
- **Resolution**: SKILL.md self-review step 4 instructs the agent to maintain an explicit counter as it applies fixes. This counter is passed to the tally fence as `--accepted N`. For `--rejected`, count `### [Code Review] Self-review` entries in `rejected-findings.md` via a Bash probe before calling the tally.
- **Source**: codebase (no prompt artifact tracks applied fixes; agent-owned counter is the only reliable mechanism)
