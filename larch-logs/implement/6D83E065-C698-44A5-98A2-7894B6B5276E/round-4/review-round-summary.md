# Review Round 4

- Mode: `diff`
- 6 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Manifest OOS count/materialization fail-closed semantics are duplicated and under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Manifest `oos_observations` counting/materialization policy is duplicated across bash, Step 2, and Python paths, with missing harness coverage. Drift or malformed JSON handling can make one path fail-open while another fails-closed, or repeatedly set `OOS_PENDING` without materialized artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Python `disposition_ok` is stricter than the bash gate for inline-triage-only evidence
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: Python returns failure when non-security OOS exists and `oos-issues.ndjson` is missing before checking inline triage/sentinel evidence, while the bash gate can pass from filed-URL evidence alone. Direct callers can get different outcomes from the same tree state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.


### FINDING_15: Manifest `focus_area` documentation does not match materialized public markdown
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-redaction-boundary-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `oos-pipeline.md` says manifest `focus_area` is preserved as a dedicated field, but public materialized blocks omit `- **focus-area**:`. Operators and gate predicates can therefore reason from docs that do not match the actual accepted markdown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-redaction-boundary-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.


### FINDING_16: Internal ship-pr disposition gate omits strict filed-URL evidence for design OOS
- **Reviewer(s)**: dyn-oos-flow-output.txt
- **Severity**: important
- **Concern**: `run_oos_disposition_gate_if_required_before_oos_pending_false` does not pass `--filed-urls-strict-file "$oos_design_path"`, unlike the checkpoint. Once pr-prep becomes gate-aligned, design OOS with already-filed strict URLs can pass checkpoint but fail internal ship clearing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Address the concern above.


### FINDING_17: Python NDJSON discovery does not mirror bash fallback when canonical run-id path is missing
- **Reviewer(s)**: dyn-python-ship-output.txt
- **Severity**: important
- **Concern**: Python only globs for alternate `oos-issues.ndjson` files when `run_id` is empty, while bash falls back when the canonical run-id path is absent. A valid single alternate NDJSON can be ignored, blocking PR creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-ship-output.txt: Address the concern above.

### FINDING_2: Design OOS path resolution docs omit the file-existence guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `oos-pipeline.md` tells the orchestrator to prefer `$DESIGN_TMPDIR/oos-accepted-design.md` whenever `DESIGN_TMPDIR` is set, but bash/Python resolvers only use that path when the file exists. A stale `DESIGN_TMPDIR` can make prompt-side filing miss the design-export fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.


