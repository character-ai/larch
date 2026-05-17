## Goal
Fix stale 2-voter competition notice, make OOS scoring symmetric (−1 for rejected OOS), bump review round cap from 3→5.

## Implementation Plan

### Goal
Three coordinated fixes: (1) update stale "2-voter primary panel" competition-notice prose to "3-voter primary panel", (2) make OOS scoring symmetric with in-scope (add -1 for rejected OOS), (3) align review-core.sh cap-reached threshold with the outer round cap.

### Files to modify

**Part 1 — Competition notice (prose updates)**

1. `scripts/render-specialist-prompt.sh` (line ~327):
   Replace heredoc body:
   - OLD: `Your findings will be voted on by a 2-voter primary panel (Codex + Cursor); Claude acts as a conditional tie-breaker only on a 1Y/1N split.`
   - NEW: `Your findings will be voted on by a 3-voter primary panel.`
   - Drop "Out-of-scope observations use **asymmetric scoring**..." sentence; replace with symmetric OOS notice: accepted OOS earns +1, rejected OOS earns -1, neutral/exonerated OOS earns 0.

2. `docs/voting-process.md`:
   - Line 7 (opening paragraph): change `a 2-voter primary panel (Cursor + Codex) and invokes Claude as a conditional tie-breaker only on a 1Y/1N split` → `a 3-voter panel (Claude + Codex + Cursor) unconditionally`
   - Line 40 (tie-breaker paragraph): remove/rewrite the `For code review, when Cursor and Codex split 1Y/1N...` paragraph since there is no longer a conditional tie-breaker.
   - Line 73 Mermaid `LAUNCH[…]` label: change `review: 2 primary + conditional Claude tie-breaker on 1Y/1N` → `review: 3 in parallel`
   - Line 110: drop asymmetric OOS scoring note (update to symmetric)
   - Line 137: drop "asymmetric reward-only for OOS" in table cell

3. `docs/point-competition.md`:
   - Line 20 and surrounding OOS Scoring section: drop "asymmetric reward-only" framing; rewrite OOS scoring table to include -1 for rejected OOS.
   - Update Scoreboard example table to include `OOS-Neutral/Exon` and `OOS-Rejected` columns.
   - Update "OOS Issue Filing" prose to match symmetric outcomes.

4. `skills/shared/voting-protocol.md`:
   - Drop the parenthetical `(OOS observations use asymmetric reward-only scoring — see OOS Scoring below — so OOS rejection carries no penalty regardless.)` from the opening paragraph.
   - OOS Scoring sub-section: rewrite to show symmetric scoring (−1 for rejected OOS).

5. Grep `docs/`, `skills/`, `agents/`, `scripts/`, `README.md`, `SECURITY.md` for residual "2-voter primary panel", "tie-break", "1Y/1N split", "asymmetric", "reward-only" prose and update consistently.

**Part 2 — Symmetric OOS scoring (code changes)**

6. `skills/review/scripts/tally-code-votes.sh` — in the `awk` block under `## Reviewer Competition Scoreboard`:
   - Add tracking for `oos_neutral[reviewer]++` (result == "neutral" or "exonerated") and `oos_rejected[reviewer]++` (all other OOS outcomes)
   - Update score formula: `score = accepted[reviewer]+0 + oos_accepted[reviewer]+0 - rejected[reviewer]+0 - oos_rejected[reviewer]+0`
   - Update `printf` to include two new columns `OOS-Neutral/Exon` and `OOS-Rejected`
   - Update header `printf` to include `OOS-Neutral/Exon | OOS-Rejected |`

7. `skills/design/scripts/tally-plan-review.sh` — same awk reshape as above (identical structure).

**Part 3 — Round cap alignment**

8. `skills/review/scripts/review-core.sh` line ~366:
   - Change `if [[ "$ROUND_NUM" -ge 3 ]]; then` → `if [[ "$ROUND_NUM" -ge 5 ]]; then`
   - This makes the inner cap-reached threshold emit truthfully for SIMPLE (outer cap 5) instead of prematurely at round 3.

9. `skills/review/SKILL.md` line ~42:
   - Change `round_cap=3` → `round_cap=5` in the standalone /review wrapper loop.

**Tests**

10. `scripts/test-render-specialist-prompt.sh`:
    - Update literal assertion for competition-notice: check for "3-voter primary panel" instead of "2-voter primary panel".
    - The negative test (no --competition-notice flag → no "Competition notice") stays unchanged.

11. `skills/review/scripts/test-tally-code-votes.sh`:
    - Add a case with OOS-rejected outcome: verify score subtracts 1 for OOS rejected.
    - Verify the new OOS-Neutral/Exon and OOS-Rejected scoreboard columns appear.

12. `skills/design/scripts/test-tally-plan-review.sh`:
    - Same OOS-rejection scoring assertion.

### Approach
- Edit sequentially. Start with Part 1 (prose), then Part 2 (awk), then Part 3 (round cap), then tests.
- Verify with `bash scripts/test-render-specialist-prompt.sh`, `bash skills/review/scripts/test-tally-code-votes.sh`, `bash skills/design/scripts/test-tally-plan-review.sh`.
- Run `pre-commit` on modified files.

### Edge cases
- Scoreboard sort order: awk output is piped through `sort` — additional columns don't affect sort behavior.
- Existing test case 1 in test-tally-code-votes.sh: OOS FINDING_3 has 2 YES / 1 NO → result="accepted", so oos_accepted increments (correct). OOS_REJECTED_COUNT=0 (unchanged for this case).
- tally-plan-review.sh uses the same score_rows.tsv pattern as tally-code-votes.sh — same awk changes apply.

## Test plan
(no test plan section in plan-file)
