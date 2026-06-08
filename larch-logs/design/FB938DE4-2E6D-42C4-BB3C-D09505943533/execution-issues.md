
### Warnings

- **Step 5b (OOS filing skipped — subsumed in-scope)**: All 6 accepted OOS items accumulated across plan-review rounds 1-5 were folded into the in-scope plan or mooted, so no separate `/larch:issue` issues were filed:
  - README/docs/SECURITY.md/plan-review.md `--approve` references → in Files-to-modify (rename sweep, accepted in-scope FINDING_2 chain).
  - Resume OR-merge mid-loop edge → folded into plan Edge cases (round-2 OOS_3).
  - Gate C summary-mode "publish without full body" → resolved by the round-3 FINDING_5 design decision (keep summary; full plan auditable via published block + log) and documented in SECURITY.md.
  - docs/configuration-and-permissions.md (round-3 OOS_1) → MOOTED: round-3 FINDING_5 reverted the full-emit fold, so `--skip-approve` does not change Gate C summary behavior and no config-doc divergence exists.
  Rationale: filing these would create GitHub issues for work already planned in-scope. Decision recorded by /design orchestrator.
