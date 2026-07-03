### OOS_1: [OUT_OF_SCOPE] Add multi-round JSONL regression coverage
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The multi-round consolidated JSONL identity path is untested, so the round-collision bug would not be caught in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Avoid double-counting degraded inputs
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Non-escalated runs without parseable classification increment two degraded counters, which makes the input-quality totals look inflated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] harness-mark wrapper parity for calibration tests
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The calibration test target’s timing wrapper is inconsistent with peer analyzer targets, which only affects timing instrumentation parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Wrap the pytest invocation with harness-mark when editing Makefile conventions.
  - From cursor-specialist-testing: Wrap with python3 python/cli.py timing harness-mark if desired.

### OOS_4: [OUT_OF_SCOPE] surface substantiality_proxy in the report
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `substantiality_proxy` is stored but never emitted in the markdown report, so operators cannot inspect that signal from CLI output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a report section or column if that signal should be visible.

### OOS_5: [OUT_OF_SCOPE] add focused calibration target to timing shard
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The focused calibration test target is not included in the timing harness shards, so local lint-only runs miss it even though CI covers it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optional: add to a harness shard for parity with voter-calibration.

### OOS_6: [OUT_OF_SCOPE] cover malformed difficulty-rating paths
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The malformed `difficulty-rating.json` path is untested, so the `unratable_malformed_rating` counter could regress without notice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a fixture with invalid JSON or missing applied_tier.

### OOS_7: [OUT_OF_SCOPE] run-root JSONL fallback precedence is a product-change question
- **Reviewer(s)**: dyn-dyn-calibration-data
- **Severity**: nit
- **Concern**: When any implement classification TSV exists, the analyzer does not fall back to run-root JSONL/NDJSON even if later-round findings only survive there; that can undercount partially slimmed corpora, but changing precedence would be a product decision rather than a plan-compliance bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-calibration-data: Address the concern above.

