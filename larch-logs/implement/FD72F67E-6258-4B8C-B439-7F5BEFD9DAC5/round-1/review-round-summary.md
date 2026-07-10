# Review Round 1

- Mode: `diff`
- 5 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_5: `price_run()` lane-field propagation is insufficiently verified
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: major
- **Concern**: `price_run()` should copy lane fields only when the source map is valid and all three component wire keys are present. Tests do not currently verify propagation for valid detailed input or `None` lane fields for malformed and aggregate fallback paths, leaving a regression that could make `/report-tokens` render aggregate-only output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_6: Cursor component wire-key ordering is untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: There is no assertion that `CURSOR_COMPOSER_COST`, `CURSOR_GROK_COST`, and `CURSOR_AUTO_COST` precede `CURSOR_COST` in `token_cost_from_args` output. A wire-order regression could silently break KV parsers and final-report or PR cost extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: Grok-only tests do not verify component values and summation
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The Grok-only flag test checks only `CURSOR_COST`, not all three component keys or the zero-valued Composer and Auto components. The detailed path could regress to blended pricing without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_8: Final-report and summary integration coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Plan-required `_final_report_token_fields` and final-summary integration tests are missing for Cursor lane splits and malformed-map fallback. Final reports or tracking summaries could omit Composer/Grok/Auto breakdowns despite correct pricing arguments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_10: Non-exact Grok model names need explicit routing coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: There is no test confirming that model keys such as `grok-4.6` or `grok-beta` route to Composer rather than receiving Grok 4.5 pricing. Add coverage for accumulation through `--cursor-input-tokens` rather than `--cursor-grok-*`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
