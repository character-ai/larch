# Voting Panel (rounds 1-3)

**Consumer**: `/review` Step 3c.1, rounds 1-3 branch.

**Contract**: owns the rounds 1-3 voting-panel body — pre-voting filter (unanimity auto-accept, nit-only auto-exonerate), two-voter setup (Cursor + Codex) with conditional Claude tie-breaker on 1Y/1N splits, proportionality guidance, ballot file handling, parallel launch ordering, threshold + competition scoring rules, the zero-accepted-findings short-circuit, the OOS artifact write rule, the save-not-accepted-IDs rule, and the rounds-4+ skip-voting rule. The `### 3c.1` heading and the rounds 1-3 / rounds 4+ branch selector remain inline in SKILL.md; this file owns the voted-rounds body content only.

**When to load**: on Step 3c.1's rounds 1-3 branch only. Do NOT load on rounds 4+ (Step 3c.1's rounds-4+ branch explicitly skips voting) or on the zero-findings short-circuit (Step 3b's skip-to-Step-4 path).

**Binding convention**: single normative source for the rounds 1-3 voting panel mechanics — pre-voting filter (unanimity auto-accept, nit-only auto-exonerate), two-voter setup (Cursor + Codex) with conditional Claude tie-breaker on 1Y/1N splits, proportionality guidance, ballot file handling rule, parallel launch ordering, threshold + competition scoring rules, the zero-accepted-findings short-circuit, the OOS artifact write rule, the save-not-accepted-IDs rule, and the rounds 4+ skip-voting rule. The `### 3c.1` heading and the "rounds 1-3" / "rounds 4+" branch selector remain inline in `SKILL.md`; this file owns the body content the rounds 1-3 branch executes. Do NOT load on rounds 4+ (Step 3c.1 explicitly skips voting in those rounds) or on the zero-findings short-circuit (Step 3b skip-to-Step-4 path).

---

## Decision Table

OOS findings are unaffected by Passes 1 and 2 — they always go to the voter panel.

| # | Scenario | Condition | Outcome | Notes |
|---|---|---|---|---|
| 1 | Pass 1 — unanimity auto-accept | Every active reviewer proposed this finding | Auto-accept; skip ballot | +1 to all proposers; if both unanimously proposed AND nit-only, Pass 1 wins |
| 2 | Pass 2 — nit-only auto-exonerate | Finding is nit-only AND `diff_mode=true` AND `SESSION_ENV_PATH` non-empty | Auto-exonerate; skip ballot | 0 pts; omit Pass 2 when either condition false |
| 3 | Post-filter: ballot empty; 0 auto-accepted; no OOS | All in-scope removed by Passes 1/2; no OOS items | Zero-in-scope short-circuit; no voters spawned | Skip to Step 4 |
| 4 | Post-filter: ballot empty; ≥1 auto-accepted; no OOS | Pass 1 cleared all in-scope; no OOS | Skip voter launch; proceed to Step 3d | Auto-accepted set is the round's result |
| 5 | Post-filter: ballot empty; OOS exists | In-scope cleared; OOS items present | Spawn voters for OOS only | Auto-accepted findings (if any) still accepted |
| 6 | Post-filter: ≥1 in-scope on ballot | At least one in-scope finding not pre-filtered | Continue with 2-voter setup | Cursor + Codex; OOS on ballot with `[OUT_OF_SCOPE]` prefix |
| 7 | 2 eligible; YES = 2 | Both Cursor and Codex voted YES | **Accept** | |
| 8 | 2 eligible; YES = 1; NO = 1 | 1Y/1N split | Invoke Claude Code Reviewer subagent as tie-breaker (Voter 3) | Apply 3-voter threshold on the combined 3-vote result (rows 9–11) |
| 9 | 3 eligible (post tie-breaker); YES ≥ 2 | Claude voted YES → 2Y total | **Accept** | |
| 10 | 3 eligible (post tie-breaker); YES = 1; EXO > NO | Claude EXONERATE → 1Y/1N/1EXO | **Exonerate** | |
| 11 | 3 eligible (post tie-breaker); YES = 1; NO ≥ EXO | Claude NO → 1Y/2N | **Reject** | |
| 12 | 2 eligible; YES = 0; all EXO | Both voted EXONERATE | **Exonerate** | 0 pts |
| 13 | 2 eligible; YES = 0; ≥1 NO | At least one NO vote | **Reject** | |
| 14 | 1 eligible primary | One of Cursor/Codex unavailable | Skip; no outcome | Not counted in accepted or rejected |
| 15 | 0 eligible | Both Cursor and Codex unavailable | Skip; no outcome | Not counted in accepted or rejected |
| 15 | Zero accepted in-scope | Voting panel accepted 0 in-scope findings | Print no-changes notice; skip to Step 4 | OOS items still routed per diff/description mode |

## Summary

- **Voters (rounds 1-3)**: Voter 1 = Codex via `run-external-agent.sh --with-effort` (→ Claude fallback if unavailable); Voter 2 = Cursor via `run-external-agent.sh --with-effort` (→ Claude fallback if unavailable). Launch both in parallel — Cursor first (slowest), then Codex. Wait via `wait-for-reviewers.sh`. **Conditional Voter 3 (tie-breaker)**: when Voters 1 and 2 split 1Y/1N, invoke Claude Code Reviewer subagent (`larch:code-reviewer`) immediately after collecting primary results; apply 3-voter threshold rules on the combined 3-vote result. Do NOT launch Claude unconditionally — only on a 1Y/1N split. Write ballot to `$REVIEW_TMPDIR/ballot.txt` using the Write tool (not a `cat` heredoc). Instruct each voter as a scrupulous senior code reviewer with proportionality guidance: vote EXONERATE rather than YES when the concern is legitimate but the proposed change introduces more complexity than it warrants.
- **OOS accepted (2+ YES in round 1)**: diff mode with non-empty `SESSION_ENV_PATH` → write to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-review.md` excluding security-tagged findings (canonical token `focus-area\s*=\s*security` anywhere in the block, case-insensitive, optional whitespace around `=`); security-tagged findings (focus-area=security) are held locally and NEVER filed publicly; **Match discrimination (false-positive guard)**: occurrences inside backtick or triple-backtick regions are fenced and do not count — only unfenced occurrences mark a finding as security-tagged; **Security counter-invariant**: real security findings MUST include at least one unfenced occurrence; each entry uses `### OOS_N:` with Description (include repo-relative file paths and line ranges when applicable, for Step 9a.1 serialization), Reviewer, Vote tally, Phase. Description mode → skip staging file; Step 4b files directly via `/umbrella --input-file`.
- **Competition scoreboard**: 7 players — Structure, Correctness, Testing, Security, Edge-cases, Codex, Claude-Generic (or Claude for both-down fallback). Scores cumulative across voted rounds 1-3. Pass 1 auto-accepted findings award +1 to all proposers. Rounds 4+ findings auto-accepted and do NOT contribute to scores.
- **Not-accepted IDs**: Record finding IDs not accepted in rounds 1-3 — voted down, exonerated by vote, or auto-exonerated by Pass 2 (exclude Pass 1 auto-accepts). In rounds 4+, suppress re-raises of any finding not accepted in rounds 1-3 (same file + same issue).
- **Full threshold and tie-break rules**: `${CLAUDE_PLUGIN_ROOT}/skills/shared/voting-protocol.md` (proportionality guidance, score formulas, ballot protocol details).
