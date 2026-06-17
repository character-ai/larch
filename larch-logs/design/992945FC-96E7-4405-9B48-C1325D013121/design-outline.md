## Proposed Design Outline

### Goals
- Replace the code-review voter panel (Claude + Codex + Cursor) with 3 archetype-distinct Cursor voters (validity-correctness, plan-fidelity-completeness, pragmatism-cost) in `/implement` Step 5 and `/review`.
- Keep the 2-of-3 majority threshold, tally, scoreboard, and point-competition machinery unchanged in behavior.
- Cut recurring Claude and Codex voter cost without changing aggregate accept decisions.

### Non-goals
- No change to the reviewer/finder panel.
- No change to `/design` plan-review voting (#4548) or main-agent-vote (MAV) voters; the default voter prompt stays byte-identical.
- No pilot, shadow-vote logging, or env kill switch; direct cutover.

### Approach sketch
- Add an optional `--archetype` to `render voter` (`python/rendering.py`) that injects one lens block; the no-archetype path stays byte-identical.
- Rewrite panel composition in `python/agent_voters.py` (`dispatch_voters`): 3 Cursor archetype slots; fall back to a single Claude floor voter when Cursor is unavailable; Codex never backfills.
- Record per-archetype identity through the existing `VOTER_N_TOOL` to `vN_tool` classification plumbing; keep historical-log parsing backward-compatible.
- Map archetype labels back to the `cursor` launch vendor where dispatch and parse-rate retry branch on tool name (`python/voting.py`).

### Surfaces in scope
- `python/agent_voters.py`, `python/rendering.py`, `python/voting.py`.
- Code-review dispatch/tally shell where touched: `python/legacy_review_shell/review-core.sh`, `tally-code-votes.sh`.
- Tests: `test_agent_voters.py`, `test_rendering.py`, `test_voting.py`.
- Docs: `docs/voting-process.md`, `docs/agents.md`, `skills/shared/voting-protocol.md`, `skills/review/SKILL.md` (preserve the `3-judge panel on every round` anchor).

### Open questions
- None. The issue settles fallback, attribution, prompt source, and scope; identity-recording details (reuse `vN_tool` vs. a separate field) resolve during plan drafting and review.
