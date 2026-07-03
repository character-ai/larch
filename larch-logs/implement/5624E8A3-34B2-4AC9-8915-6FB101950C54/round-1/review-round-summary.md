# Review Round 1

- Mode: `diff`
- 6 accepted, 3 rejected (7 neutral)

## Accepted Findings

### FINDING_1: design escalation uses round-total highs
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-tier-resume
- **Severity**: important
- **Concern**: Design escalation in `plan_review_loop.py` keys off new high findings instead of the round-total accepted high count, so a duplicate high plus a new high can fail to escalate to HARD and never authorize round 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use round-total `high >= DESIGN_ESCALATION_HIGH_ACCEPTED_THRESHOLD` for escalation; add regression test for cumulative-two-high case.
  - From codex-specialist-correctness: Base the escalation threshold on current-round total high accepted count, not high_new.
  - From cursor-specialist-edge-cases: Use `high >= DESIGN_ESCALATION_HIGH_ACCEPTED_THRESHOLD` for escalation; keep `high_new` for continuation only; add a cross-round regression test.
  - From cursor-specialist-testing: Add continuation tests locking intended semantics; align code with plan if round-total was required.
  - From codex-specialist-testing: Use the round-total `high >= 2` for escalation, keep duplicate/new logic for convergence reasons, and add a regression test for one duplicate plus one new high finding.
  - From dyn-dyn-tier-resume: Gate escalation on cumulative round-total `high >= DESIGN_ESCALATION_HIGH_ACCEPTED_THRESHOLD` (the `high` variable already computed at lines 756-759), keep the one-new-high no-escalate case, and add a regression test for cumulative-two-high across rounds.


### FINDING_2: round-3 authorization is too broad
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Design cap-3 authorization can be granted from bare `high-accepted` or generic continuation reasons, letting HARD reviews reach round 3 without a recorded escalation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Restrict round-3 authorization to escalated-high-accepted and explicit substantiality reasons; exclude bare high-accepted.
  - From codex-specialist-correctness: Authorize cap 3 only from explicit round-3 authorization, such as an escalation record or escalated-high-accepted.
  - From cursor-specialist-edge-cases: Limit authorization to escalated-high-accepted structural-or-large-change degraded-panel and difficulty-rating.json escalations list.


### FINDING_3: run-log refresh drops tier resolution data
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-tier-resume
- **Severity**: important
- **Concern**: `_refresh_difficulty_record` rebuilds difficulty records instead of merging them, so it can stringify escalations and drop override, tier, and `TierResolution` fields needed for resume and calibration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Call difficulty write-record merge path or preserve override_source panel_tier round_cap codex_model_role audit_evaluated escalated_round and dict escalations.
  - From codex-specialist-correctness: Use the merge-preserving difficulty write path or explicitly carry forward all audit, override, escalation, and TierResolution fields.
  - From cursor-specialist-edge-cases: Route refresh through write_record_main merge path; preserve dict escalations and operator override without floor recomputation.
  - From dyn-dyn-tier-resume: Route refresh through write_record_main / _merge_existing_record_fields, pass escalation objects through unchanged, and forward all TierResolution fields explicitly.


### FINDING_4: bootstrap merge keeps stale difficulty tiers
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Existing difficulty records can short-circuit resolution and keep stale `applied_tier` or `panel_tier` values after a real rating arrives, leaving later steps stuck on the bootstrap tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Treat audit_evaluated None as unresolved or avoid bootstrap resolution fields; preserve resolved tier fields only after override, audit, or escalation.
  - From codex-specialist-edge-cases: Only preserve the existing applied/panel tier fields when they came from an operator override, audit upgrade, or escalation. Otherwise let the new rating/floors recompute the tier fields.


### FINDING_6: existing non-override records bypass audit upgrade
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: Ordinary difficulty records already carry `panel_tier`, so resolve-panel early-returns and non-override runs never persist the required audit decision.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Treat existing records with `audit_evaluated is None` as unresolved for audit purposes when `audit_enabled=true`, persist the audit decision, and add a non-override audit-upgrade regression test.


### FINDING_16: design tier resolution ignores plan metadata sidecar
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: Design plan review can synthesize MODERATE from missing override data even when the plan itself says HARD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Before resolving the panel tier, seed or merge `difficulty-rating.json` from `design-difficulty-rating.raw.json` or `plan.txt` metadata, then call `resolve_panel_tier`; cover HARD plan metadata and raw-rating cases in `test_plan_review.py`.


