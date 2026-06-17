## Proposed Design Outline

### Goals
- Replace the code-review voter trio (Claude + Codex + Cursor) with three Cursor voters, each carrying a distinct archetype, in `/implement` Step 5 and `/review` via the shared `scripts/dispatch-code-voters.sh`.
- Cut recurring per-round voter cost/latency (drop the Claude and Codex voter lanes) while keeping the 2-of-3 majority and the existing tally/scoreboard machinery.

### Non-goals
- No change to the reviewer/finder panel.
- No change to `/design` plan-review voting (#4548, on hold).
- No shadow-vote pilot, no env kill-switch: direct, clean replacement.

### Approach sketch
- In `dispatch-code-voters.sh`, render three Cursor voter prompts, each with a distinct archetype (Validity/Correctness, Plan-Fidelity/Completeness, Pragmatism/Cost), and launch all three through `agent dispatch-waterfall` (three cursor slots) instead of the Claude+Codex+Cursor trio.
- Add a voter-archetype render path (`python/cli.py render voter --archetype <name>`) that injects one prioritized lens onto the full acceptance rubric; reuse existing finder lens wording where it fits.
- Cursor-unavailable fallback: a single Claude voter (the existing floor), decided by the binding-single threshold; no revert to the full legacy panel.
- Per-archetype scoreboard labels so point-competition does not collide on three same-vendor voters; keep the 2-of-3 tally and threshold table otherwise unchanged.

### Surfaces in scope
- `scripts/dispatch-code-voters.sh` (+ sibling `.md`, `scripts/test-dispatch-code-voters.sh`)
- `python/cli.py render voter` rendering module and voter prompt template
- Voter-archetype prompt definitions (new, or reuse `skills/shared/reviewer-templates.md` lenses)
- Tally / point-competition attribution (`python/voting.py` and scoreboard surfaces)

### Open questions
- Archetype prompt source: new voter-archetype templates vs reuse of finder archetype bodies (resolve during Step 2b drafting from the actual render code).
- Exact Claude-floor fallback wiring (single-voter threshold) and whether point-competition needs explicit per-archetype keys or already supports distinct slot labels.
