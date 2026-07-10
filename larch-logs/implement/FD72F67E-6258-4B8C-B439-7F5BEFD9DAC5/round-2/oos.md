### FINDING_4: [OUT_OF_SCOPE] Fallback retains stale Cursor lane fields
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: `_fallback_cost()` does not clear Cursor lane fields when blended fallback pricing is used. Re-pricing failure or reuse of a detailed `RunRecord` can leave stale lane splits alongside a new blended `cursor_cost`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Progress report still uses Composer-only Cursor pricing
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: `progress_report` still prices all Cursor usage with Composer-only argv flags. After MODERATE Grok coder routing lands, mid-run progress summaries may mis-price or inflate Grok usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Mixed cohorts suppress available Cursor lane breakdowns
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Scans mixing legacy and model-aware runs show aggregate Cursor only even when partial lane data exists. The all-or-nothing rendering gate should be documented or changed to sum available lane fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
