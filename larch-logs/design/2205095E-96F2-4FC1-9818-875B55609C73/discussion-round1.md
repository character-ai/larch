# Design Discussion — Round 1 (Scope & Constraints)

Issue #4538 — replace the code-review voter panel (Claude+Codex+Cursor) with 3 archetype-distinct Cursor voters in `/implement` Step 5 and `/review`.

## Decision 1: Rollout strategy
- **Question**: Direct cutover, shadow-vote pilot first, or cutover + shadow-log the old panel?
- **Resolution**: Direct cutover. Replace the voter panel now with 3 Cursor archetypes. No pilot, no shadow logging.
- **Source**: user

## Decision 2: Panel composition
- **Question**: Pure 3-Cursor archetypes, or keep one non-Cursor voter as a hedge?
- **Resolution**: Pure 3-Cursor. Three Cursor voters, each with a distinct archetype (Validity/Correctness, Plan-Fidelity/Completeness, Pragmatism/Cost). No Claude or Codex hedge voter in the normal panel.
- **Source**: user

## Decision 3: Cursor-unavailable fallback
- **Question**: When Cursor is down for a round, revert to the legacy multi-vendor panel or fall back to Claude floor only?
- **Resolution**: Claude floor only. A single Claude voter for that round (the existing floor). Do NOT revert to the full legacy 3-vendor panel.
- **Source**: user

## Decision 4: Scoreboard attribution
- **Question**: With three same-vendor Cursor voters, how should point-competition attribute votes?
- **Resolution**: Per-archetype attribution. Each archetype is its own competitor (distinct labels) so per-voter scoring stays meaningful and same-vendor keys do not collide.
- **Source**: user

## Decision 5: Rollback path
- **Question**: Add an env kill-switch to revert to the legacy panel, or clean replacement?
- **Resolution**: Clean replacement, no env switch. Smallest diff, no dead legacy path. Rollback is a git revert.
- **Source**: user

## Scope boundaries (from issue body)

**In scope**
- Voters only, in `/implement` Step 5 and `/review`, both via the shared `scripts/dispatch-code-voters.sh`.
- New concept: archetype variants for voters (archetypes exist only for finders today).
- Keep 3 voters and the 2-of-3 majority acceptance threshold.

**Out of scope (must not change)**
- The reviewer/finder panel (vendor diversity proven there per #3635).
- `/design` plan-review voting (#4548, ON HOLD).
- Scoring rubric semantics, OOS handling, and the review-loop structure (only voter identity/attribution changes).

**Hard constraints**
- Preserve the 2-of-3 majority threshold and the existing tally, scoreboard, and point-competition machinery (adapt attribution only).
- Each archetype applies the FULL review-acceptance rubric but prioritizes one lens; a voter must never reject a real correctness/security defect on its own lens's grounds. Lens 1 (correctness/security) takes precedence over lens 3 (pragmatism).
- Accept the known aggregate drift (outcomes flip on ~9.8% of findings; accept rate 51.3% to 49.5%); the goal is rough aggregate stability, not identical decisions.
