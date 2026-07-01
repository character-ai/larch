## Decision 1: Round-2 prune policy under cap=2
- **Question**: A reviewer that produced no accepted findings in round 1 is the pivotal case. How aggressively should round-2 pruning drop such reviewers?
- **Resolution**: Drop quiet reviewers. Prune any reviewer with no net-accepted value in round 1; keep the acceptance-floor rule, retuned for the 1-round window. Maximize convergence-at-round-1 (the Cursor/latency win). Round 2 is a genuine backup that runs only when round 1 was productive. Safety comes from preserving the #5733 `-output` join fix plus a new regression test that the round-1 ledger populates non-zero counts before round 2 relies on it.
- **Source**: user

## Constraint: Preserve #5733 join fix
- **Resolution**: Do not regress the `_normalize_code_label` `-output` stripping in `review_prune.py`. A join-key mismatch there records all-zero productivity and prunes the whole panel at round 2. Add a regression test that a productive round-1 panel yields non-zero ledger counts.
- **Source**: codebase / issue

## Constraint: Reuse #5255 prune-to-empty convergence
- **Resolution**: "No reviewers eligible for round 2 -> converged at round 1" is the cap=2 instance of the existing #5255 prune-to-empty completion path. Reuse it. Do not reintroduce a re-probe round.
- **Source**: codebase / issue

## Constraint: Cap literal surface list mirrors #3662
- **Resolution**: Move the cap-of-5 to 2 across every site #3662 touched: `ROUND_CAP` in `plan_review_common.py`, the `--round-cap` default in `review_and_fix.py`, the round-cap fallback in `round_runner.py`, and the round-guard in `review_prune.py` (`round_num <= 2 or round_num >= 5`). Cap = 2 must hold for /implement Step 5, /review, and /design plan review.
- **Source**: codebase / issue

## Constraint: Out of scope
- **Resolution**: No voter, aggregator, coder, or availability-policy changes. Model bump touches only reviewer specialist `model_role` -> `CODEX_DEFAULT_MODEL` (gpt-5.5). A missing vendor drops its half of the pair with no cross-vendor or Claude backfill; the pair itself is the redundancy.
- **Source**: user / issue
