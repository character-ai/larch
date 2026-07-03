# Review Round 2

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Missing `started_at` should not create `unknown` month rows
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-calibration-data
- **Severity**: important
- **Concern**: The drift “By Month” table is still bucketing runs with missing or unparsable `manifest.started_at` into a synthetic `unknown` month, which skews month distribution instead of excluding those runs or rendering `n/a`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Skip records with started_month is None in _render_drift, consistent with _render_audit_deltas exclusion rules.
  - From cursor-specialist-edge-cases: Skip runs where started_month is None in _render_drift or render n/a; add a fixture asserting undated runs are excluded.
  - From codex-specialist-edge-cases: Skip records whose `started_month` is `None` in the “By Month” drift table, or render a separate `n/a` diagnostic outside the month distribution.
  - From cursor-specialist-testing: Skip records where started_month is None in _render_drift and add a test asserting those runs are absent from the By Month table
  - From codex-specialist-testing: Skip `by_month` aggregation when `record.started_month is None`, while still including the run in the rater-model drift table if appropriate, and add a regression fixture for missing/bad timestamps.
  - From dyn-dyn-calibration-data: Skip runs whose `started_month` is `None` in `_render_drift()` (same rule as audit pairing), or emit a separate `n/a` row instead of the `unknown` bucket; add a fixture asserting a run with bad/missing `started_at` does not appear under `unknown`.


### FINDING_3: Under-rating burden must only count identity-matched sidecar rows
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing, dyn-dyn-calibration-data
- **Severity**: important
- **Concern**: `_sidecar_note()` can count sidecar verdicts for under-rated runs even when there are no accepted identities, so false-negative burden can be inflated or misattributed instead of being joined only to the relevant findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Count sidecar rows for the under-rated run by the sidecar’s `source_skill/run_id` and, if exact validation is needed, carry all classification identities not just accepted identities.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Count sidecar rows joined by `source_skill`, `run_id`, `round_num`, and `finding_id` without requiring them to also be accepted classification identities; add a fixture where a confirmed rejected finding annotates an under-rated run.
  - From dyn-dyn-calibration-data: Treat an empty accepted-identity set as “no joinable findings”: return `confirmed=0` (or `confirmed=n/a` when burden is undefined), or invert the filter to `if not accepted_keys or _sidecar_row_matches(row, accepted_keys)` so only identity-matched rows increment verdict counts.


### FINDING_5: Pre-audit tier should return `None` when no recoverable tier exists
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `pre_audit_tier` falls back to `difficulty.tier_max()` and silently maps runs with no recoverable source or floor tier to `TRIVIAL`, instead of returning `None` so they render `n/a` and are excluded from peer matching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Build the pre-audit candidate list explicitly and return `None` when no source tier or floor tier is present.
  - From codex-specialist-edge-cases: Build the normalized base tier list first; if both that list and `floor_tiers` are empty, return `None` instead of calling `tier_max()`.


