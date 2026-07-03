### OOS_1: [OUT_OF_SCOPE] review-core stub tier mapping can drift from production
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The review-core test stub derives shape/cap behavior from `--tier` inside the harness, so it can drift from production difficulty calibration or emission behavior without a failing test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: The review-core stub hardcodes tier→`PANEL_SHAPE`/cap mapping instead of importing `larch.calibration.difficulty`. Acceptable per plan, but it can drift from `config.py` without a harness failure.
  - From cursor-specialist-edge-cases: review-core.env shape/cap assertions validate stub echo not production. Production could stop emitting tier metadata while argv checks still pass via stub self-mapping. Out of scope: rely on argv assertions or call real review-core.

### OOS_2: [OUT_OF_SCOPE] design tier tests are redundant
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The TRIVIAL and MODERATE design dispatch cases assert the same manifest/model-role behavior, so they do not provide distinct tier-regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: TRIVIAL and MODERATE design `panel-dispatch` tests assert identical manifest shape and `model_role=review` because design dispatch does not vary slot count by tier. Why OOS: redundant coverage, not a regression risk; both cases are plan-required.
  - From cursor-specialist-edge-cases: TRIVIAL and MODERATE tier dispatch tests assert identical expectations. No unique tier regression signal between those two tiers in design panel dispatch. Out of scope: tiers share production behavior; merge or differentiate only if design singles land.

### OOS_3: [OUT_OF_SCOPE] escalated prune fixture lacks a negative control
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The round-3 escalated prune case does not pair the positive path with a same-fixture `--escalated-round false` control, so the bypass proof is narrower than it could be.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Escalated prune bypass has no paired `--escalated-round false` control in the same fixture. Why OOS: the ledger setup is correct for round-3 pruning; round-2 prune behavior is covered elsewhere (`test_panel_dispatch_prunes_round_two_empty_panel`, `test_filter_pruned_round_two_prunes_unproductive_rows`).

### OOS_4: [OUT_OF_SCOPE] continuation escalation bash case is weaker than pytest
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The bash continuation-elevation check overlaps the Python continuation coverage but asserts fewer fields, so it is a weaker hardening signal rather than a distinct regression guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Continuation escalation bash case overlaps existing Python continuation tests. Missing trigger/round fields in JSON check is weaker than pytest coverage. Out of scope: optional harness hardening only.

### OOS_5: [OUT_OF_SCOPE] round argument propagation is not asserted
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: nit
- **Concern**: The implement review-token propagation harness records the round argument, but no case checks that the wrapper actually forwards a non-default round number.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.

