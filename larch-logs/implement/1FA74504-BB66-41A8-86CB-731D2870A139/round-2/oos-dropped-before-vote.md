### OOS_1: [OUT_OF_SCOPE] Symlinked JSONL should be rejected at discovery
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Classification path discovery is allowing symlinked JSONL inputs to be selected before read-time rejection, so symlinked findings files are discovered and then fail later instead of being excluded up front.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Reject symlinks in _classification_paths or mirror _read_text symlink policy at discovery.
  - From cursor-specialist-edge-cases: Reject symlinks in _classification_paths or treat symlink discovery as missing source.

### OOS_2: [OUT_OF_SCOPE] Audit-delta tests need floors_applied coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-calibration-data
- **Severity**: latent
- **Concern**: Audit-delta test coverage still misses the case where `floors_applied` raises the pre-audit tier, so floor-raised peer matching could regress without a failing fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add a fixture where floors_applied raises pre-audit tier and assert peer matching uses the raised tier.
  - From cursor-specialist-testing: Add an audited/unaudited pair where floors_applied raises pre_audit_tier and assert peer matching uses the floored tier.
  - From dyn-dyn-calibration-data: Add an audited/unaudited pair where floors_applied raises pre_audit_tier and assert peer matching uses the floored tier.

### OOS_3: [OUT_OF_SCOPE] Report renderers need smoke assertions
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-calibration-data
- **Severity**: important
- **Concern**: Report renderers do not have enough smoke assertions, so dropping a `render_report()` section could ship without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Add fixture assertions for each section header and at least one expected row per table
  - From dyn-dyn-calibration-data: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Difficulty-calibration target is missing from harness shards
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The focused `test-difficulty-calibration` target is not included in the harness shard list, so local `make test-harnesses` runs can miss this calibration target even though CI still covers it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optionally add test-difficulty-calibration to a harness shard for parity with voter-calibration

### OOS_5: [OUT_OF_SCOPE] Stable cross-round JSONL IDs should collapse
- **Reviewer(s)**: dyn-dyn-calibration-data
- **Severity**: latent
- **Concern**: Stable JSONL `id` values are only collapsed for `skill == "design"`, while implement/review paths still key on `round_num:fallback_id`, so a run with a stable cross-round id but no `finding_hash` can over-count accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-calibration-data: Address the concern above.

