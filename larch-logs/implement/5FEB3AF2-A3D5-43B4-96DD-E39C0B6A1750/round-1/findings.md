### FINDING_1: Launcher short-output whitelist diverges from validator
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The degraded-response whitelist in `launch-review.sh` uses weaker substring and shape checks than the validator. This can both degrade validator-accepted compact outputs such as pretty-printed JSON or inline TSV, and incorrectly accept prose that merely mentions `"no_issues_found": true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: First-nonblank-line extraction is duplicated across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Three production scripts duplicate identical first-nonblank-line `awk` logic, creating risk that future sentinel or whitespace semantics diverge between launcher, collector, and dispatch gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Launcher output classification lacks a single final decision path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Post-`jq` `OUTPUT` handling in `launch-review.sh` uses sequential writers instead of one mutually exclusive decision chain, making it easy for later edits to overwrite degraded-response classification with empty-response classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: NS-retry success paths can promote sentinel outputs to OK
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `collect-agent-results.sh` assigns `STATUS=OK` on NS-retry success paths without re-running `_classify_sentinel_status`, so a retry output beginning with `CURSOR_DEGRADED_RESPONSE` can be promoted to OK on paths that otherwise classify sentinels as non-OK.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Dispatch pattern-gate setup is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `dispatch-with-waterfall.sh` repeats `check_file` resolution and readability checks for two pattern flags, increasing maintenance cost for future gates or error-message changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Launcher degraded heuristic thresholds are magic numbers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `1000` token and `500` byte degraded-response thresholds are inline constants, making them harder to tune, document, and keep aligned with tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Byte/token degraded heuristic can misclassify legitimate short reviews
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The byte/token heuristic can mark legitimately short high-token prose as `CURSOR_DEGRADED_RESPONSE`, while threshold edge cases may still allow compact narration-only outputs to remain `STATUS=OK` on ungated paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Waterfall integration tests do not exercise high-token degraded Cursor output
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The waterfall Cursor stub hardcodes `outputTokens=1`, so integration tests never exercise the degraded-response heuristic for high-token narration-only Cursor output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Validator test case does not assert required STATUS line
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-validate-research-output.sh` Case 19h checks exit code 5 but not the required `STATUS=CURSOR_EMPTY_RESPONSE` stdout contract, so CI could miss a broken status emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Per-job local fix loop clamp lacks path-specific coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New `normalize_rcc_max_iter` call sites in per-job local verification and fix-loop paths lack harness coverage, so invalid `LARCH_CI_LOCAL_FIX_ITER` values could bypass clamping despite helper-only tests passing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Bash 3.2 collector contract doc omits Case 5b
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-collect-agent-bash32.md` omits Case 5b from the documented harness catalog, hiding always-on degraded sentinel coverage from maintainers using the contract doc.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Security docs still describe Cursor review as plan mode
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Security and operator docs still describe legacy Cursor plan-mode behavior and omit the active `--mode ask`, dual read-only mode notes, `CURSOR_DEGRADED_RESPONSE`, and collector sentinel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Degraded detection trusts client-reported outputTokens
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The launcher relies on `usage.outputTokens` from the same Cursor JSON envelope as `.result`, so a compromised or buggy client can under-report token usage and bypass degraded-response detection for narration-only output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Collector and validator sentinel-body semantics differ
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Collector sentinel classification uses only the first line, while validator literal matching uses the full trimmed body; this is safe but creates inconsistent telemetry for sentinel-first outputs with trailing prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Branch bundles unrelated design re-entry commit
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch also includes unrelated #2935 work, including plugin version bumps, `larch-logs/implement/`, and design-guard changes outside the #2995 plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Cursor probe doc still references omitted plan mode
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/check-reviewers.md` still documents the Cursor probe as intentionally omitting `--mode plan`; the source reviewer marked this as outside the #2995 plan rather than a plan violation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
