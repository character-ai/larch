# Discussion Round 1 — Issue #3619 (redesign)

Context: the prior /design run on this issue was truncated by a since-fixed bug (only 1 review round ran after operator approval). This run replaces the in-body plan via the full flow with multi-round review.

## Decision 1: Plan baseline
- **Question**: Should the replacement plan start from the prior in-body plan (which absorbed 13 accepted findings from the one review round that ran) or be re-derived fresh from the problem statement?
- **Resolution**: Refresh the prior plan. Keep its reviewed architecture (`scripts/reviewer-prune.sh` helper with `record`/`filter` subcommands, run-stable ledger TSV, filtered-manifest-is-authoritative contract) as the baseline; update it against the current codebase and the landed #3662 end state. The full multi-round panel re-reviews the refreshed draft this run.
- **Source**: user

## Decision 2: Re-probe policy (no-redemption ratchet)
- **Question**: Can a combo pruned at round 3 ever return — strict ratchet, periodic re-probe, or round-5 full re-probe?
- **Resolution**: Round-5 full re-probe. Rounds 1-2 full panel; rounds 3-4 prune combos with zero accepted items in their last 2 launched rounds; round 5 (the cap) always relaunches the full panel.
- **Source**: user

## Decision 3: #3662 dependency state
- **Question**: Is the prior plan's "Depends on #3662 (flat review-round cap of 5)" still a pending dependency?
- **Resolution**: #3662 is CLOSED [DONE] and landed: `scripts/lib-implement-round-cap.sh` is deleted and `review-implement-step5-loop.sh` uses a fixed `ROUND_CAP:-5`. The refreshed plan builds on this landed state ("builds on", not "depends on") and still makes no cap edits of its own. Verified separately: the feature itself is NOT implemented (`scripts/reviewer-prune.sh` absent; no commit references #3619).
- **Source**: codebase

## Hard constraints carried forward (from issue + refreshed baseline)
- Scope: `/design` plan review, `/implement` Step 5 code review, `/review` diff mode. `/review` description mode is single-pass and never prunes.
- Rounds 1-2 spawn the full panel unconditionally; pruning is mechanical (ledger-driven), never orchestrator discretion.
- Fail open: missing/unparsable ledger → all slots eligible.
- Pruned-empty rounds advance the round counter; they are never degraded rounds and never convergence.
- `LARCH_REVIEWER_PRUNE=off` restores today's behavior everywhere.
- No review-round-cap edits in this issue (#3662 owns the flat cap of 5, already landed).

3 decisions resolved.
