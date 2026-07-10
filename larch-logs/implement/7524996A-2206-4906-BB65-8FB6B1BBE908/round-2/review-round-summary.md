# Review Round 2

- Mode: `diff`
- 3 accepted, 11 rejected (0 neutral)

## Accepted Findings

### FINDING_1: CI launcher misses `-m` when recording the model
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The Codex launcher only recognizes `--model`, so launches that use `-m` can be recorded under the wrong model and token reports may be mis-bucketed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_2: CI launcher applies fix-role pins to the wrong modes
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The shared CI launcher applies fix-role and auto model pins during conflict recovery too, so rebase conflict fallback can run with the wrong Codex or Cursor model instead of preserving the conflict defaults.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_4: Resolved model is stamped too early
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: The panel manifest and voter path pre-fill `resolved_model` with the tier default, bypassing env override > default_model > role default precedence and causing downstream progress/cost reports to mis-bucket the run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


