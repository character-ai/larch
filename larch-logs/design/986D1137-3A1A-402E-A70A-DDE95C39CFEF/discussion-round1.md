## Decision 1: Scope is test/harness coverage ONLY
- **Question**: Does this issue permit any runtime behavior change, or is it strictly test/harness code?
- **Resolution**: Strictly test/harness code. NO runtime behavior changes; every changed line must be test or harness code. The runtime (difficulty tiers, 2/2/3 ceilings, escalation, tier→panel mapping) already shipped in PR #6122 and is verified working. If a "test" would require a runtime edit to pass, that is a signal the assertion is wrong, not that the runtime needs changing.
- **Source**: codebase (issue #6170 body: "No runtime behavior changes; every changed line is test or harness code")

## Decision 2: Exactly three coverage gaps at their current successor surfaces
- **Question**: Which surfaces receive new coverage, and are any adjacent paths in scope?
- **Resolution**: Three gaps only. (1) `skills/implement/scripts/test-implement-review-token-propagation.sh` — add `--difficulty` acceptance + tier→`--panel` token mapping (TRIVIAL→simple, MODERATE/HARD→hard) + `PANEL_SHAPE` propagation cases. (2) `skills/design/scripts/test-step3-review-cap.sh` — add HARD round-3-reachable, design escalation-trigger, and Gate-C authorized-cap cases. (3) `python/tests/review/test_plan_review_panel.py` — add per-tier Codex model-role + always-pairs shape checks (the successor to the long-deleted `test-dispatch-plan-review-panel.sh`, mirroring `test_review_pipeline.py` code-review-side tests). No new files. The 6 "non-gap" paths listed in the issue need no action.
- **Source**: codebase (issue #6170 gaps 1-3 + non-gaps list)

## Decision 3: Acceptance is the three make targets passing
- **Question**: What is "done"?
- **Resolution**: `make test-implement-review-token-propagation`, `make test-step3-review-cap`, and `make test-dispatch-plan-review-panel` all pass with the new cases; no runtime diff.
- **Source**: codebase (issue #6170 Acceptance section)
