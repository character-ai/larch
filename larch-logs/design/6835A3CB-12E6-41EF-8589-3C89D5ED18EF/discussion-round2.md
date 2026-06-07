# Discussion Round 2 — Issue #3619 (post-Gate-C amendment)

## Decision 1: De-duplicate cap-removal scope against in-flight #3662
- **Question**: Phase-2 dep-analysis during OOS filing revealed #3662 ([IMPLEMENTING]) already covers the /implement cap-inflation removal (entry inflation, post-round bump, lib-implement-round-cap.sh deletion, Step 5 telemetry fence → ROUND_CAP=5) and flattens the /design Gate C cap SIMPLE 3 → 5. Amend the approved plan before the Step 5c write, or publish as-is?
- **Resolution**: Amend, then publish without a second review panel (change is subtractive + stale-fact fixes). Drop the duplicated cap scope; state that #3619 builds on #3662's flat-cap-5 end state; fix the SIMPLE edge-case note (round-5 re-probe reachable on both tiers); add a native blocked-by edge #3619 ← #3662. The prune-skipped loop-advancement edits remain in scope here.
- **Source**: user
