# Voting Panel (rounds 1-3)

**Consumer**: `/review` Step 3c.1, rounds 1-3 branch.

**Contract**: owns the rounds 1-3 voting-panel body — pre-voting filter (unanimity auto-accept, nit-only auto-exonerate), two-voter setup (Cursor + Codex) with conditional Claude tie-breaker on 1Y/1N splits, proportionality guidance, ballot file handling, parallel launch ordering, threshold + competition scoring rules, the zero-accepted-findings short-circuit, the OOS artifact write rule, and the save-not-accepted-IDs rule. The `### 3c.1` heading and the rounds 1-3 branch selector remain inline in SKILL.md; this file owns the voted-rounds body content only.

**When to load**: on Step 3c.1's rounds 1-3 branch only. Do NOT load on the zero-findings short-circuit (Step 3b's skip-to-Step-4 path).

**Binding convention**: single normative source for the rounds 1-3 voting panel mechanics — pre-voting filter (unanimity auto-accept, nit-only auto-exonerate), two-voter setup (Cursor + Codex) with conditional Claude tie-breaker on 1Y/1N splits, proportionality guidance, ballot file handling rule, parallel launch ordering, threshold + competition scoring rules, the zero-accepted-findings short-circuit, the OOS artifact write rule, and the save-not-accepted-IDs rule. The `### 3c.1` heading and the "rounds 1-3" branch selector remain inline in `SKILL.md`; this file owns the body content the rounds 1-3 branch executes. Do NOT load on the zero-findings short-circuit (Step 3b skip-to-Step-4 path).

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
| 8 | 2 eligible; YES = 1; EXO = 1 | One YES, one EXONERATE | **Exonerate** | No tie-breaker; 1 YES < 2 required; EXO counts as legitimate concern |
| 9 | 2 eligible; YES = 1; NO = 1 | 1Y/1N split | Invoke Claude Code Reviewer subagent as tie-breaker (Voter 3) | Apply 3-voter threshold on the combined 3-vote result (rows 10–12) |
| 10 | 3 eligible (post tie-breaker); YES ≥ 2 | Claude voted YES → 2Y total | **Accept** | |
| 11 | 3 eligible (post tie-breaker); YES = 1; EXO > NO | Claude EXONERATE → 1Y/1N/1EXO | **Exonerate** | |
| 12 | 3 eligible (post tie-breaker); YES = 1; NO ≥ EXO | Claude NO → 1Y/2N | **Reject** | |
| 13 | 2 eligible; YES = 0; all EXO | Both voted EXONERATE | **Exonerate** | 0 pts |
| 14 | 2 eligible; YES = 0; ≥1 NO | At least one NO vote (0Y/2N or 0Y/1N/1EXO) | **Reject** | EXO does not override NO when YES = 0 |
| 15 | 1 eligible primary | One of Cursor/Codex unavailable | **Skip voting — all findings accepted** | Per voting-protocol.md threshold rules: < 2 eligible voters → fall back to accepting all; print `**⚠ Voting skipped (1 voter available, minimum 2 required). All findings accepted.**` |
| 16 | 0 eligible | Both Cursor and Codex unavailable | **Skip voting — all findings accepted** | Per voting-protocol.md threshold rules: 0 eligible → fall back to accepting all; print `**⚠ Voting skipped (0 voters available, minimum 2 required). All findings accepted.**` |
| 17 | Zero accepted in-scope | Voting panel accepted 0 in-scope findings | Print no-changes notice; skip to Step 4 | OOS items still routed per diff/description mode |

## Summary

- **Voters (rounds 1-3)**: Voter 1 = Codex via `run-external-agent.sh --with-effort`; Voter 2 = Cursor via `run-external-agent.sh --with-effort`. Launch both in parallel — Cursor first (slowest), then Codex. Wait via `wait-for-reviewers.sh`. When one primary voter fails, the eligible count drops to 1 and voting is skipped (row 15). When both fail, voting is skipped entirely (row 16). **Conditional Voter 3 (tie-breaker)**: when Voters 1 and 2 split 1Y/1N, invoke Claude Code Reviewer subagent (`larch:code-reviewer`) immediately after collecting primary results; apply 3-voter threshold rules on the combined 3-vote result. Do NOT launch Claude unconditionally — only on a 1Y/1N split. Write ballot to `$REVIEW_TMPDIR/ballot.txt` using the Write tool (not a `cat` heredoc). Instruct each voter as a scrupulous senior code reviewer with proportionality guidance: vote EXONERATE rather than YES when the concern is legitimate but the proposed change introduces more complexity than it warrants. **Voter column labels in the per-finding vote breakdown table**: use `Codex` for Voter 1, `Cursor` for Voter 2, and `Claude` for the tie-breaker (Voter 3). Do NOT use a model name (e.g., `Claude-Opus`, `Claude-Sonnet`) as a column header.
- **OOS accepted (2+ YES in round 1)**: diff mode with non-empty `SESSION_ENV_PATH` → write to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-review.md` excluding security-tagged findings (canonical token `focus-area\s*=\s*security` anywhere in the block, case-insensitive, optional whitespace around `=`); security-tagged findings (focus-area=security) are held locally and NEVER filed publicly; **Match discrimination (false-positive guard)**: occurrences inside backtick or triple-backtick regions are fenced and do not count — only unfenced occurrences mark a finding as security-tagged; **Security counter-invariant**: real security findings MUST include at least one unfenced occurrence; each entry uses `### OOS_N:` with Description (include repo-relative file paths and line ranges when applicable, for Step 9a.1 serialization), Reviewer, Vote tally, Phase. Description mode → skip staging file; Step 4b files directly via `/umbrella --input-file`.
- **Competition scoreboard**: hard panel — 12 players: Structure, Correctness, Testing, Security, Edge-cases, Plan-fidelity, Codex-Structure, Codex-Correctness, Codex-Testing, Codex-Security, Codex-Edge-cases, Codex-Plan-fidelity. Simple panels additionally include Claude-Generic. Both-down fallback uses Claude only. Scores cumulative across voted rounds 1-3. Pass 1 auto-accepted findings award +1 to all proposers.
- **Not-accepted IDs**: Record finding IDs not accepted in rounds 1-3 — voted down, exonerated by vote, or auto-exonerated by Pass 2 (exclude Pass 1 auto-accepts).
- **Full threshold and tie-break rules**: `${CLAUDE_PLUGIN_ROOT}/skills/shared/voting-protocol.md` (proportionality guidance, score formulas, ballot protocol details).
