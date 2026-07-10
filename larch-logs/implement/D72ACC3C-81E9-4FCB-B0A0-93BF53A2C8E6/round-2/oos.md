### FINDING_1: [OUT_OF_SCOPE] Progress summaries misprice Grok Cursor usage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-routing-parity
- **Severity**: minor
- **Concern**: Round-level and progress-summary Cursor cost breadcrumbs still emit only Composer-priced `--cursor-*` flags and do not use the Grok-specific counters. A MODERATE Step 2 Grok run can therefore show inflated Cursor cost in mid-run round summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Reuse `cursor_argv_from_buckets` (or equivalent model split) in `_round_vendor_cost_argv` when `BUCKETS_cursor_by_model` is present.
  - From cursor-specialist-edge-cases: Route progress_report Cursor argv through cursor_argv_from_buckets or equivalent grok/composer split.
  - From cursor-specialist-testing: Extend `_round_vendor_cost_argv` to reuse `cursor_argv_from_buckets` when by-model buckets exist.
  - From dyn-dyn-routing-parity: Round-summary cost calculation still emits only surcharged Composer `--cursor-*` flags and never the new grok-specific counters, so in-run Step 2 progress/round costs for MODERATE Cursor work can overstate Cursor spend when grok-4.5 tokens are present.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Resume routing can preserve a stale coder
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Resume bootstrap skips `_phase_coder` and restores the persisted `coder` from routing state. A stalled MODERATE run that saved `coder=codex` can resume into Codex Step 2 despite Cursor being available, missing the MODERATE Cursor-first routing path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Re-run difficulty-keyed implicit coder selection on resume when no explicit `--coder` is supplied and the effective tier changed.
  - From cursor-specialist-testing: Add a resume+MODERATE regression test and either re-select implicit coder on resume or document and test intentional coder freeze.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Direct run summaries omit Grok and auto Cursor flags
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-routing-parity
- **Severity**: minor
- **Concern**: `render_run_summary_main()`’s `_TOKEN_COST_ARGS` and argparse surface omit the Grok and auto Cursor token flags. Direct run-summary CLI recomputation can therefore ignore Grok usage and misprice aggregate Cursor cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extend `_TOKEN_COST_ARGS` and argparse with grok-4.5 and auto Cursor flags, then price via shared token-cost helpers.
  - From dyn-dyn-routing-parity: `render_run_summary_main()`’s `_TOKEN_COST_ARGS` still omits the grok and auto Cursor token flags, so direct CLI summary recomputation can ignore grok usage and misprice aggregate Cursor cost.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Empty-model Cursor buckets default to Composer
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Empty-model Cursor rows still default to `composer-2.5` in by-model buckets. Missing model attribution on a Grok run can silently price usage at Composer Teams rates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Default empty model to the effective implement model when known, or fail closed when MODERATE Grok usage lacks model attribution.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Blended fallback ignores by-model Cursor buckets
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The blended Cursor fallback ignores `BUCKETS_cursor_by_model` when token-cost parsing fails. Grok-heavy runs in the fallback path can therefore be priced at Composer-blended rates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Teach the blended fallback to consult by-model Cursor buckets before defaulting to Composer-blended rates.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Token splitting hardcodes the Grok model slug
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-routing-parity
- **Severity**: minor
- **Concern**: Token splitting hardcodes `grok-4.5` while routing reads `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY`. If the configured model slug changes without updating the literal, MODERATE Cursor runs can launch the configured model but record tokens under the Composer bucket, silently mispricing totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Drive the split key from the shared config constant instead of a literal string.
  - From dyn-dyn-routing-parity: Derive the Grok bucket key from a single shared constant (for example `config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY[config.DIFFICULTY_TIER_MODERATE]`) in both launch routing and token splitting, and add a test that asserts the config value and pricing split stay aligned.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Step 2 dispatch documentation is stale
- **Reviewer(s)**: dyn-dyn-routing-parity
- **Severity**: minor
- **Concern**: The Step 2 dispatch contract still says difficulty is forwarded only to Codex launches, while the implementation now forwards it to Cursor as well. Stale contract text can mislead future routing changes and reviews.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
