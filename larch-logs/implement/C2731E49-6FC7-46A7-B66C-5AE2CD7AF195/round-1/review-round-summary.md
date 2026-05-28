# Review Round 1

- Mode: `diff`
- 13 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: Resume can clear emergency state and audit metadata
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Resume/re-entry paths can overwrite or lose `EMERGENCY_REQUESTED=true` when `--emergency` / `--emergency-requested true` is omitted, causing run flags, metadata, final summaries, and downstream audit visibility to disagree with the emergency fallback that actually occurred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_10: Final-summary rendering lacks false/omitted emergency test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-render-run-summary.sh` does not explicitly assert that false or omitted emergency state suppresses the Emergency line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Bootstrap lacks invalid emergency argv harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `implement-bootstrap.sh` lacks a test for invalid `--emergency-requested` argv values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Invalid bypass-log fallback may leak unsanitized content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Invalid `emergency-bypass.log` fallback appends raw log bytes without secret redaction, unlike the valid-path append tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_19: SKILL stdout scan omits EMERGENCY_REQUESTED
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_ib_kv_scan` does not parse `EMERGENCY_REQUESTED`, so the orchestrator exports it but may never refresh it from bootstrap stdout for downstream steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Emergency preflight behavior lacks executable regression coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Emergency Preflight bypass/refusal semantics live primarily in prompt prose, so regressions in missing-plan bypass, malformed-plan handling, or `AUDIT=refuse` behavior may pass existing lint and structure checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_20: Final report silently treats invalid emergency flag as false
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write-final-report.sh` silently maps invalid `EMERGENCY_REQUESTED` values in `run-flags.sh` to false, hiding emergency status instead of failing closed or warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_21: Fatal versus fallback bypass-log behavior is undocumented
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `mktemp` failure is the only fatal path in bypass-log append handling, while other invalid-log paths fall back; this asymmetry is not documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: Emergency bypass kind tokens are underspecified
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Preflight mandates bypass log grammar but does not define canonical `kind=` tokens for malformed-plan and audit-refuse cases, risking inconsistent audit trails and downstream tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Dirty-tree recovery prose omits emergency resume argument
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The dirty-tree recovery prose omits `--emergency-requested` from the Step 0 resume argument list, so operators following prose rather than the code block may resume without the flag and trigger emergency state loss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: Bypass-log documentation disagrees with warn-and-continue behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `implement-bootstrap.md` says invalid `emergency-bypass.log` lines fail closed with `STEP_FAILED`, but the script records an invalid-format warning and continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: Emergency bypass log can be replayed twice on resume
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `resume-plan-tail` can append the same `emergency-bypass.log` again, duplicating bypass warnings in `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Emergency cases missing from harness documentation table
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/test-implement-bootstrap.md` omits emergency-related cases that exist in the shell harness, creating misleading maintenance documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


