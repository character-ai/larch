## Goal
Implement issue #5089: [IMPLEMENTING] [BUG] Implement final report prints a factually incorrect statement about costs.

## Implementation Plan
```
  Cost is the per-round vendor cost (Codex + Cursor + Claude subprocess), attributed by token-ledger timestamp window; it excludes main-agent Claude, so it is less than the run Cost line above. Rendered as an em dash when per-round timing or the token ledger is unavailable.
```
The costs summary line in the final report:
```
  /implement run 9F2F9905-6D7B-45EF-86AA-32CDF976E444 — merged

  - Mode: N/A
  - Emergency: true
  - Duration: 01:52:29
  - Cost: 💰 TOTAL ~$30.42 — Claude $18.84, Codex $7.98, Cursor $2.46, Claude (subprocess) $1.14  |  Tokens: 34762k
  - Issue: #5078 — https://github.com/character-ai/larch/issues/5078
  - PR: #5088 — https://github.com/character-ai/larch/pull/5088
  - Plan review: N/A
  - Dynamic archetypes: ok (1)
  - Code review: 2/3 accepted
  - Lines (PR diff): code +211/-8, larch-logs +573/-0
  - OOS filed: 0
  - Exec issues: 0
  - Warnings: 1
  - Run logs: larch-logs/implement/9F2F9905-6D7B-45EF-86AA-32CDF976E444/
```
which appeared above that statement clearly includes Claude main agent cost report (the first item on the Cost: line).  I believe this statement is not just incorrect, it is also useless, and should be eliminated.

## Test plan
(no test plan section in plan-file)
