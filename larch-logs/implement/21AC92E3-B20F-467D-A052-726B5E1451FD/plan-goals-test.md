## Goal
Implement issue #5264: [IMPLEMENTING] [BUG] Review round Gantt chart missing the step of cursor applying review review suggestions (and I want it shown).

## Implementation Plan
```
PR #5263 merged. Per NEVER #17, emitting the extracted final-summary marker body verbatim:

/implement run 206037F9-BABA-4679-94AA-EB3DE105DF9D — merged

- Mode: N/A
- Emergency: true
- Duration: 01:38:46
- Cost: 💰 TOTAL ~$46.10 — Claude $15.29, Codex $22.61, Cursor $6.05, Claude (subprocess) $2.15  |  Tokens: 69035k
- Issue: #5255 — https://github.com/character-ai/larch/issues/5255
- PR: #5263 — https://github.com/character-ai/larch/pull/5263
- Plan review: N/A
- Dynamic archetypes: ok (1)
- Code review: 1/2 accepted
- Lines (PR diff): code +57/-37, larch-logs +543/-0
- OOS filed: 0
- Exec issues: 0
- Warnings: 3
- Run logs: larch-logs/implement/206037F9-BABA-4679-94AA-EB3DE105DF9D/
- Main agent model: claude-opus-4-8
- Effort: max
- Larch version: 51.3.16

<!-- larch:run-summary v=1 -->

Exec Issues and Warnings

Exec Issues (0):
Warnings (3):
1. Step implement-bootstrap emergency-bypass-log — /implement --emergency preflight bypassed (exit 0)
2. code-review panel (round 1): 4 finding(s) decided below the 2-of-3 panel quorum due to per-item JUDGE_ERROR (FINDING_7, FINDING_8, FINDING_9, FINDING_10); resolved by the remaining voter(s).
3. Step 7a — session-transcript status=captured: session transcript was written; commit deferred to caller.

Review Phase Detail

┌───────────────────┬─────────────┬──────────┬──────────────┬──────────────┬─────────┬────────┬───────────┐
│       Round       │ Suggestions │ Accepted │ OOS proposed │ OOS accepted │  Time   │  Cost  │ Reviewers │
├───────────────────┼─────────────┼──────────┼──────────────┼──────────────┼─────────┼────────┼───────────┤
│                 1 │           2 │        1 │            3 │            0 │ 30m 16s │ $28.66 │         8 │
├───────────────────┼─────────────┼──────────┼──────────────┼──────────────┼─────────┼────────┼───────────┤
│ Total (round-sum) │           2 │        1 │            3 │            0 │ 30m 16s │ $28.66 │         8 │
└───────────────────┴─────────────┴──────────┴──────────────┴──────────────┴─────────┴────────┴───────────┘

The Total (round-sum) row adds up the per-round Suggestions and Accepted: when the review loop re-raises the same finding across rounds, that finding is counted once per round, so the round-sum can exceed the number of distinct findings. Top reviewers counts per-round accepted-point scores the same way.

Finding decomposition (canonical, scope-aware): round 1: 5 finding(s) = 2 in-scope (voted; matches the headline X/Y accepted) + 3 out-of-scope. The Suggestions and OOS columns above count findings by finding id (raw per-finding) and can disagree with this scope-aware split when findings are reclassified out-of-scope after voting; round-meta.json records both raw (tally) and canonical (tally_canonical) counts so downstream joins do not contradict.

Round 1 reviewer timing

Round 1 reviewer timing  ·  window 0:00-30:16 (1816s)
                                        0:00                                               30:16
                                       ┌────────────────────────────────────────────────────────┐
codex/edge-cases                       │█████                                                   │ 144s
codex/dyn-dyn-review-convergence-codex │█████                                                   │ 157s
cursor/correctness                     │██████                                                  │ 205s
cursor/testing                         │███████                                                 │ 210s
cursor/edge-cases                      │████████                                                │ 244s
codex/correctness                      │████████                                                │ 257s
cursor/dyn-dyn-review-convergence      │████████                                                │ 271s
codex/testing                          │██████████                                              │ 330s
aggregator                             │          ██                                            │  71s
aggregator                             │            ████                                        │ 108s
cursor/pragmatism-vote                 │                ██                                      │  75s
cursor/plan-fidelity-vote              │                ███                                     │  91s
cursor/validity-vote                   │                ███                                     │ 114s
cursor/edge-cases                      │                   █████                                │ 145s
cursor/testing                         │                   █████                                │ 145s
codex/correctness                      │                   █████                                │ 149s
cursor/dyn-dyn-review-convergence      │                   █████                                │ 162s
cursor/correctness                     │                   ██████                               │ 166s
codex/edge-cases                       │                   ██████                               │ 169s
codex/testing                          │                   ██████                               │ 176s
codex/dyn-dyn-review-convergence-codex │                   █████████                            │ 273s
aggregator                             │                            ██                          │  73s
cursor/plan-fidelity-vote              │                              ██                        │  49s
cursor/pragmatism-vote                 │                              ██                        │  62s
cursor/validity-vote                   │                              ██                        │  64s
                                       └────────────────────────────────────────────────────────┘

Top reviewers (by per-round accepted-point score, whole run):
1. codex/correctness — 2
2. codex/edge-cases — 2
3. codex/testing — 2
4. cursor/correctness — 2
5. cursor/dyn-dyn-review-convergence — 2
6. cursor/edge-cases — 2
7. cursor/testing — 2

Reviewer slot failures: 0

✻ Baked for 2m 30s

※ recap: Implemented issue #5255 (review loop converges on prune-to-empty panels for /design and /implement) via emergency mode; PR #5263 is merged. Next: run the Step 18 stall-recovery gate and teardown to finish the run.

❯ what happened in the above Gantt chart after the voters?  It looks like almsost 15 minutes blank?

Good eye. Let me verify against the actual round timing data before explaining (the tmpdir ledgers are still intact pre-teardown):

  Ran 1 shell command

Verified from the timing ledger. That blank stretch is Cursor applying the accepted review fix — not idle time.

What the gap is:
- The chart window is the full round-1 duration: 1816s (30:16).
- The reviewer/aggregator/voter slots all finish by ~17:16 (two waves: the initial degraded panel, then the fresh-panel retry, then voting).
- The timing ledger shows a cursor-review-fix row: start t≈17:24, end t≈30:13, duration 769s (~12m 49s), tool=cursor. That is your "blank ~13-15 min."

Why it renders blank:
- The chart is titled "Round 1 reviewer timing" — it plots only reviewer-family slots (reviewers, aggregator, voters).
- The coder fix-application (cursor-review-fix) and post-round checks are not reviewer slots, so they draw no bar. The window still spans the whole round, so the trailing coder time shows as empty space.

What was being applied: the single accepted finding (FIX_COUNT=1, CODER_STATUS=applied) — the /design completion-marker correctness fix to plan_review.py. Cursor took ~12.8 min to apply and validate it, which dominated the back half of the round.

So: reviewers ~17 min, then ~13 min of fix-application by Cursor. The chart just doesn't visualize the coder lane.
```

## Test plan
(no test plan section in plan-file)
