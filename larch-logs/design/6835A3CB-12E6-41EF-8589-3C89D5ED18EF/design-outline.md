## Proposed Design Outline

### Goals
- From round 3 on, skip reviewer combos (tool × archetype) with zero accepted items in their last 2 launched rounds; round 5 re-probes with the full panel.
- Apply to all three round loops: /design plan review, /implement Step 5, /review diff mode.
- Keep savings measurable and reversible: one env-var escape hatch; visible via /report-tokens.

### Non-goals
- No cross-run persistence — pruning state derives from the current run's per-round artifacts.
- No changes to voters, judges, the dynamic-archetype scout, or vote thresholds.
- No token-weighted allocation (stays a docs/point-competition.md future plan).

### Approach sketch
- New shared stdlib-only helper computes the eligible combo set for round N from per-round launch manifests + findings-classification TSVs (accepted = voted-in, incl. accepted OOS).
- Hook it into the two panel dispatch sites: `dispatch-panel.sh` (/review + /implement) and `dispatch-plan-review-panel.sh` (/design); rounds 1-2 and 5 bypass with full panels.
- All-combos-pruned → skip the round (zero-findings convergence breadcrumb), spawn nothing.
- Hard-cap rounds at 5: remove the /implement degraded-round cap inflation.
- Fail open: missing/corrupt history artifacts → full panel.

### Surfaces in scope
- `skills/review/scripts/` (dispatch-panel.sh, review-core.sh) and `skills/design/scripts/` (dispatch-plan-review-panel.sh, plan-review-loop.sh, run-step3-review.sh).
- `scripts/run-step5-review.sh`, `skills/review-and-fix/scripts/review-implement-step5-loop.sh` (cap inflation removal).
- New shared prune helper + offline test harness; docs (`docs/voting-process.md`, `docs/configuration-and-permissions.md`); Makefile lint/test registration.

### Open questions
- None.
