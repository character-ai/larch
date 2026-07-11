# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Stale Cursor per-slot auto documentation
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-cursor-routing
- **Severity**: major
- **Concern**: `docs/review-agents.md:99` still states that Cursor reviewer rows use per-slot `auto`, while runtime routing and adjacent documentation resolve the default to Composer 2.5. This is incorrect operator-facing guidance and can evade the current acceptance grep because `cursor` and `auto` are not adjacent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-cursor-routing: Address the concern above.


### FINDING_2: Missing explicit Cursor auto-rate fallback tests
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: `python/tests/report/test_report_tokens_cost.py` lacks focused assertions that the legacy `("cursor", "auto")` rate row is absent and that `rate_row("cursor", model="auto")` falls back to the Composer 2.5 default rates. A future rate-table or fallback regression could therefore pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_3: Missing Composer 2.5 default-resolution integration coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: `_run_coder_cursor` lacks coverage that an unmocked model-resolution path produces `--model composer-2.5` in the launch arguments. A routing regression could remain hidden when tests mock resolved model arguments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_4: Missing Cursor model-resolution failure coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: `_run_coder_cursor` lacks coverage for `resolve_model_args` raising an exception. The documented unavailable-tier behavior could regress without asserting that the function returns `False` and does not launch Cursor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
