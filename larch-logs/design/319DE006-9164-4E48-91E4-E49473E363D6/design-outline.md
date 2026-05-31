## Proposed Design Outline

### Goals
- Stop each review loop at the first calm round, not after two consecutive rounds.
- Raise the accepted-findings bound from 3 to 5; keep the "0 important accepted" gate.
- Apply the same relaxation to both loops: `/design` plan review and `/implement` code review.

### Non-goals
- No new env vars or tunable flags. Hardcode the bound (5) and the single-round rule.
- Do not touch the hard round cap (`LARCH_DESIGN_ROUND_CAP` / `--round-cap`).
- Do not change zero-findings convergence, degraded-round handling, or the churn warning.

### Approach sketch
- `plan-review-loop.sh`: remove the streak machinery; converge when one non-degraded round has ≤5 accepted and 0 important. Replace the `LOOP_REASON=streak` token.
- Remove `LARCH_DESIGN_CONVERGENCE_THRESHOLD` and the `--convergence-threshold` flag; hardcode 5.
- `review-and-fix.sh`: drop the two-round (`round >= 2` + prev-round) requirement; converge on a single non-degraded round (≤5 accepted, 0 important). Remove its `--convergence-threshold` flag; hardcode 5.
- Update SKILL.md prose, the `.md` contracts, references, and docs to match.
- Update both test suites and the `test-design-structure.sh` pin.

### Surfaces in scope
- `skills/design/scripts/plan-review-loop.sh` (+ `.md`), `skills/design/SKILL.md`
- `skills/review-and-fix/scripts/review-and-fix.sh` (+ `.md`)
- `skills/design/references/flags.md`, `references/plan-review.md`, `docs/configuration-and-permissions.md`, `docs/installation-and-setup.md`
- Tests: `test-plan-review-loop.sh`, `test-design-multi-round-integration.sh`, `test-design-structure.sh`, `test-review-and-fix.sh`, `test-step3-review-cap.sh`

### Open questions
- New `LOOP_REASON` token for `/design` convergence (replacing `streak`) — propose `converged`; finalize in the plan.
