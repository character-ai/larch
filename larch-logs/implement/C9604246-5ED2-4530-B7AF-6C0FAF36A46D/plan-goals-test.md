## Goal
Implement issue #5442: [IMPLEMENTING] [BUG] Review Phase Detail in final report in /implement (possibly /design too) seems to be using old buggy cost computation.

## Implementation Plan
```
---LARCH-SUMMARY-FINAL-BEGIN---
/implement run 6F041614-C184-47B2-8548-4730B70E44F6 — merged

- Mode: N/A
- Duration: 04:17:15
- Cost: 💰 TOTAL ~$23.57 — Claude $4.60, Codex-5.5 $2.19, Codex-mini $7.30, Cursor $6.09, Claude (subprocess) $3.39  |  Tokens: 88275k
- Issue: #5402 — https://github.com/character-ai/larch/issues/5402
- PR: #5437 — https://github.com/character-ai/larch/pull/5437
- Plan review: N/A
- Dynamic archetypes: ok (2)
- Code review: 0 findings
- Lines (PR diff): code +132/-45, larch-logs +584/-0
- OOS filed: 0
- Exec issues: 0
- Warnings: 0
- Run logs: larch-logs/implement/6F041614-C184-47B2-8548-4730B70E44F6/
- Main agent model: claude-sonnet-4-6
- Effort: max
- Larch version: 52.0.4

<!-- larch:run-summary v=1 -->

Review Phase Detail

┌───────────────────┬─────────────┬──────────┬──────────────┬──────────────┬────────────┬────────┬───────────┐
│       Round       │ Suggestions │ Accepted │ OOS proposed │ OOS accepted │    Time    │  Cost  │ Reviewers │
├───────────────────┼─────────────┼──────────┼──────────────┼──────────────┼────────────┼────────┼───────────┤
│                 1 │           0 │        0 │           10 │            0 │ 3h 41m 14s │ $57.67 │        10 │
├───────────────────┼─────────────┼──────────┼──────────────┼──────────────┼────────────┼────────┼───────────┤
│ Total (round-sum) │           0 │        0 │           10 │            0 │ 3h 41m 14s │ $57.67 │        10 │
└───────────────────┴─────────────┴──────────┴──────────────┴──────────────┴────────────┴────────┴───────────┘
```
Note the difference between report Cost line:
```
- Cost: 💰 TOTAL ~$23.57 — Claude $4.60, Codex-5.5 $2.19, Codex-mini $7.30, Cursor $6.09, Claude (subprocess) $3.39  |  Tokens: 88275k
```
and round 1 of review reported cost in the table:
```
  │                 1 │           0 │        0 │           10 │            0 │ 3h 41m 14s │ $57.67 │        10 │
```
Note that we have recently fixed a bug whereby cost computation was just using the vendor (Codex) without the model to look up costs per token, which is a BIG mistake, as they differ by also 7X between GPT 5.5 and GPT 5.4 mini

## Test plan
(no test plan section in plan-file)
