### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Grok pricing lacks dated provenance
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-routing-parity
- **Severity**: minor
- **Concern**: The new `grok-4.5` rate row lacks the plan-required dated pricing provenance and first-party surcharge-exemption comment. Operators and future audits cannot verify why Grok is priced at 2.00/0.50/6.00 without the Teams surcharge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a dated 2026-07-10 source comment beside `CURSOR_GROK_4_5_BASE` and the `("cursor", "grok-4.5")` rate row, citing cursor.com models-and-pricing and the forum exemption note.
  - From cursor-specialist-testing: Add a dated source comment beside `CURSOR_GROK_4_5_BASE` documenting cursor.com pricing and the first-party exemption.
  - From codex-specialist-testing: Add the dated Cursor documentation and forum-thread-165207 staff-confirmation comment beside `CURSOR_GROK_4_5_BASE`.
  - From dyn-dyn-routing-parity: Add a dated comment beside `CURSOR_GROK_4_5_BASE` and the rate-table entry citing the July 2026 Cursor models-and-pricing docs and the first-party exemption rationale, matching the existing Composer surcharge comment style.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: MODERATE Cursor launcher integration test is incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No integration test asserts that the MODERATE Cursor launcher argv includes `--model grok-4.5` without mocking `resolve_model_args`. A regression in difficulty forwarding or default-model wiring could launch `composer-2.5` while tests remain green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend `test_cursor_launcher_builds_agent_argv` with `--difficulty MODERATE` and assert captured argv contains `--model grok-4.5`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_7: `run_dispatch` does not verify effective-difficulty propagation
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `run_dispatch_main` lacks a test that resolved tmpdir difficulty is forwarded to `step2-dispatch --difficulty`. The wrapper could stop propagating effective difficulty while direct Step 2 tests continue to pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a `run_dispatch` test with override/prior fixtures that asserts the spawned Step 2 argv includes the resolved `--difficulty`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_10: Difficulty resolver lacks malformed and unreadable-input tests
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Tests omit required missing, malformed, and unreadable resolver-input cases. A read or parsing behavior change could route an uncertain tier without regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add parameterized absent, malformed, and read-failure cases that assert an empty effective tier unless a valid higher-precedence source exists.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_11: Model-override precedence lacks Grok-default coverage
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Tests do not prove that environment and plugin overrides beat the MODERATE Grok caller default. A precedence regression could launch or attribute `composer-2.5` instead of honoring an explicit Cursor override.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Test `resolve_model_args` with `default_model=grok-4.5` under each override and with both overrides present.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_12: External dispatch lacks effective-difficulty routing coverage
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Step 2 external-dispatch coverage lacks effective-difficulty routing assertions. MODERATE Cursor-first routing or invalid-tier registry fallback could regress at the integration surface without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add fixtures for MODERATE, invalid, and missing effective difficulty that assert map selection and registry fallback.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0
