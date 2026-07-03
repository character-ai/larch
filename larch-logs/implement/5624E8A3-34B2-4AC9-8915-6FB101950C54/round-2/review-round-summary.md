# Review Round 2

- Mode: `diff`
- 5 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Cap-3 authorization is too broad
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `design_escalation_authorized()` still treats generic continuation reasons, including `non-nit-accepted`, `structural-or-large-change`, and `degraded-panel`, as enough to authorize HARD round 3. That can let a design run reach or expose round 3 without a recorded high-severity escalation or difficulty-record escalation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_2: Override re-entry keeps stale tier
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: `resolve_panel_tier()` can reuse a persisted resolution when `resolved_once` and `existing_operator_override` are true, even if a new `--difficulty` override is passed. On resume or re-entry, that can preserve the old tier instead of recomputing the updated tier fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_3: Progress metadata omits persisted difficulty state
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: `_round_difficulty_object()` still reads only `scout-difficulty-rating.raw.json` and always emits empty escalations. As a result, `round-meta.json` can lose audit upgrades, override source, tier, cap, model role, and escalation entries from the persisted difficulty record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_5: `/review` prompt still documents old caps
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: The active `/review` skill text still talks about a two-round safety limit and `PANEL_SHAPE=simple|hard`. That can mislead prompt-side consumers to stop HARD reviews too early or branch on the wrong shape token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_6: `/design` references still describe the old cap contract
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: The active `/design` reference docs still describe fixed cap-2 behavior, round-2 backup logic, and default-role dispatch in places that now need tier-specific cap and pruning rules. Prompt-side Gate C or Step 3 recovery can therefore follow stale instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
