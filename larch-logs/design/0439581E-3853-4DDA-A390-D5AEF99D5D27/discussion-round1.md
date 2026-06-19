## Decision 1: Pruning criterion
- **Question**: Which precision signal triggers pruning a reviewer combo over its trailing window?
- **Resolution**: Either signal trips — prune when net score ≤ 0 (sum accepted − sum rejected over window) OR acceptance rate below the floor. Replaces today's `accepted_count == 0` rule.
- **Source**: user

## Decision 2: Trailing window
- **Question**: What lookback window should the precision signal use?
- **Resolution**: Keep the 2-launched-round window. Aggregate the score over the last 2 launched rounds; still require ≥2 rounds of recorded history before a combo is prunable (same lookback as today).
- **Source**: user

## Decision 3: Acceptance-rate floor
- **Question**: Below what acceptance rate (accepted/total findings, summed over the 2-round window) should a net-positive combo still be pruned?
- **Resolution**: Below 1/3. Implemented as a module-level constant — no new env knob. Zero-findings combos are already pruned by the net-score ≤ 0 arm (matches today's accepted==0), so no divide-by-zero.
- **Source**: user

## Decision 4: Cross-skill scope (in-scope, single shared function)
- **Question**: Does the change touch only `/review`, or also `/design` plan review?
- **Resolution**: The prune logic lives in shared functions in `python/review_pipeline.py` (`reviewer_prune_record`, `reviewer_prune_filter`, `_ledger_history`, `derive_prune_status`) consumed by `/review` (code review + `/implement` Step 5 via `review_and_fix.py`) AND `/design` plan review (`plan_review_panel.py`). One shared change updates both paths; no per-caller fork.
- **Source**: codebase

## Decision 5: Token allocation out of scope
- **Question**: Does this change include token allocation weighting?
- **Resolution**: No. Token allocation remains "Future Plans" per `docs/point-competition.md`; this change only makes the conditional-spawning prune decision precision-aware.
- **Source**: codebase / issue

## Decision 6: Ledger schema + preserved behaviors
- **Question**: What ledger and behavior changes are required vs. preserved?
- **Resolution**: `reviewer-prune-ledger.tsv` gains a `rejected_count` column (for net score) and a total/findings count column (for acceptance rate); ledger is run-local so no cross-run migration. Preserve unchanged: rounds 3–4 prune window, round-5 full re-probe, fail-open on ledger read errors, and the `LARCH_REVIEWER_PRUNE=off` disable knob.
- **Source**: codebase

Decisions resolved: 6.
