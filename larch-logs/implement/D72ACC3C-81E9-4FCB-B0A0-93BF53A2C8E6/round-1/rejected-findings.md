### [rejected] FINDING_4

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_4: Pricing provenance for the Grok rate is undocumented
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: The new `grok-4.5` pricing row lacks the required dated source comment documenting Cursor pricing provenance and the first-party surcharge exemption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Cursor Grok pricing duplicates the model identifier instead of using shared configuration
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-routing-parity
- **Severity**: minor
- **Concern**: Token splitting and cost calculation key off the literal `grok-4.5`, while launch routing uses `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY`. A future model-slug change could leave tokens in the Composer bucket and miscalculate `CURSOR_COST`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-routing-parity: Derive the grok bucket key from the same config constant used by the Cursor launcher (for example `config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY[config.DIFFICULTY_TIER_MODERATE]`) and price it via `rate_row("cursor", model=...)` instead of a duplicated literal/base map.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Cursor rows without a model silently default to Composer pricing
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Empty-model Cursor rows default to `composer-2.5` during by-model aggregation, so a Moderate Grok run with missing model attribution can be silently priced at Composer rates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Partial Cursor by-model reports can undercount aggregate usage
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: When `BUCKETS_cursor_by_model` is present but incomplete, aggregate-only Cursor tokens are discarded, producing understated `CURSOR_TOKENS` and `CURSOR_COST`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_10: Launcher override precedence lacks Moderate Grok coverage
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Launcher tests do not verify environment and plugin model overrides against the Moderate `grok-4.5` caller default, so precedence regressions could launch or attribute the wrong Cursor model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add MODERATE launcher tests for both overrides and retain blank or invalid override coverage.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: Cursor usage recording is not verified to preserve the resolved model
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The launcher test does not verify that the resolved model is passed into Cursor usage recording, which could prevent `BUCKETS_cursor_by_model` from pricing the Grok lane correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Capture the usage-recording call and assert model=grok-4.5, then verify the recorded row reaches model-split pricing.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_12: Resume bootstrap can preserve a stale vendor across difficulty changes
- **Reviewer(s)**: dyn-dyn-routing-parity
- **Severity**: minor
- **Concern**: Resume bootstrap skips `_phase_coder` and preserves the prior `coder`, so an earlier Codex selection can survive after the effective difficulty changes to Moderate, causing Step 2 to dispatch Codex instead of the difficulty-preferred Cursor Grok lane.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-routing-parity: On resume, when `--coder` is not explicit, re-run the difficulty-keyed implicit coder selection (or invalidate/restage `coder` when the effective tier’s preferred first vendor differs from the persisted value) before Step 2 dispatch.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0
