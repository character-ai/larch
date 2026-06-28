## Goal
Implement issue #5714: [IMPLEMENTING] [BUG] Nested `claude` subprocess empty-output / exit-124 root cause is untracked across 3 lanes; #5677 only retried the design voter.

## Implementation Plan
#### Summary

The nested `claude` subprocess (launched via `python/cli.py agent launch-claude-subprocess`) intermittently returns **empty output / exit 124 / "Error: No messages returned from query"**. This one failure mode surfaces in **three independent lanes**, but only per-lane symptom mitigations exist. The shared root cause was filed as **#5636 and closed NOT_PLANNED**, so it is currently untracked.

#### The three affected lanes

| Lane | Tracking issue | What shipped |
|---|---|---|
| `/design` Step-3 plan-review Claude voter | #5677 (closed, PR #5712) | **one retry** on empty/124 |
| `/implement` Step-7a code-flow diagram | #5674 (closed, PR #5705) | fast-fail only (timeout 600→180s) |
| `/implement` claude-ci lint-fixer | #5605 (closed) | fast-fail / auth-preflight only |

Only the design voter now retries. The code-flow and lint-fixer lanes still fast-fail with no retry, so they degrade on the same transient that #5677 now tolerates. There is no parity and no root-cause fix.

#### Evidence (last ~55 `/design` runs, audit on 2026-06-28)

- **13 of the last 55 `/design` runs** had a 0-byte `claude-vote-output.txt`; **6 of those were at the current v52.1.5** (so the symptom was live right up to the #5677 fix).
- The `claude-vote-output.txt.failure-diag` / `.stderr` sidecars show **"Error: No messages returned from query" (5x)** vs **"claude subprocess timed out" (1x)** in the recent window. The dominant proximate cause is the empty-query result, not a wall-clock timeout.
- Overall empty-vote rate across all design runs: Claude **13/304 = 4.3%**, Codex 6/314 = 1.9%, Cursor 2/312 = 0.6% (Claude lane is the worst by ~2x).
- The `claude.ai connectors are disabled...` auth warning is a **red herring** — #5677 confirmed it prints on the ~41/50 successful votes too.

#### Why #5677 is not a complete fix

- It is **design-voter-scoped** (`python/larch/review/plan_review_panel.py::dispatch_voters`); the code-flow and lint-fixer lanes get nothing.
- It is a **single retry that treats the failure as transient**. If the failure is systemic (e.g., an auth/permission-mode interaction), one retry only reduces, not eliminates, the rate.
- It did **not** action the root-cause bullet from #5677's own body: investigate `--permission-mode plan` vs an active `ANTHROPIC_API_KEY` in the shared launcher.

#### Suggested fix

1. **Root cause**: investigate the `--permission-mode plan` / `ANTHROPIC_API_KEY` precedence path in the shared launcher `python/larch/agents/agents.py` (and `agent_voters.py`). Determine why the nested `claude` returns no messages, not just how to retry it.
2. **Parity**: if the root cause is not quickly fixable, extend the #5677 one-retry-on-empty/124 pattern to the code-flow lane (`python/larch/implement/step_7a.py` / `skills/implement/scripts/generate-code-flow-diagram.sh`) and the claude-ci lint-fixer lane.
3. **Observability**: surface the retried/failed subprocess lane in run-log diagnostics so the rate is trackable across all three lanes, not just the design voter.

#### References

- #5636 (root cause, closed NOT_PLANNED), #5677 (design-voter retry, PR #5712), #5674 (code-flow fast-fail, PR #5705), #5605 (lint-fixer fast-fail), #5637 (panel degrade-to-2/3 resilience). Surfaced by a post-merge audit of the last ~50 `/design` and `/implement` run logs.

## Test plan
(no test plan section in plan-file)
