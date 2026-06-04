### FINDING_1: Manifest OOS count/materialization fail-closed semantics are duplicated and under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Manifest `oos_observations` counting/materialization policy is duplicated across bash, Step 2, and Python paths, with missing harness coverage. Drift or malformed JSON handling can make one path fail-open while another fails-closed, or repeatedly set `OOS_PENDING` without materialized artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Design OOS path resolution docs omit the file-existence guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `oos-pipeline.md` tells the orchestrator to prefer `$DESIGN_TMPDIR/oos-accepted-design.md` whenever `DESIGN_TMPDIR` is set, but bash/Python resolvers only use that path when the file exists. A stale `DESIGN_TMPDIR` can make prompt-side filing miss the design-export fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Python design-OOS tests are misnamed or too weak for their asserted behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-python-ship-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: Several `python/test_ship.py` names imply PR creation after disposition, but the assertions expect `NEEDS_USER_INPUT` / first-pass blocking. Weak or misleading assertions could invite future “fixes” that break design-export OOS blocking coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-python-ship-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] OOS public sanitization/redaction is inconsistent and not mechanically enforced end-to-end
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-redaction-boundary-output.txt
- **Severity**: important
- **Concern**: Redaction is duplicated between materialization and prompt-side OOS filing/logging, while later Step 9a.1 outputs rely on orchestrator discipline rather than a shared helper. Public OOS issues, NDJSON, logs, or raw manifests can retain PII, internal URLs, or novel secret formats.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-redaction-boundary-output.txt: Address the concern above.

### FINDING_5: Python and bash OOS handoff ladders duplicate policy without a parity contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Python PR-create OOS handling mirrors bash `pr-prep` in a separate large block plus `_oos_gate`; future fixes to trigger ordering or security-OOS behavior can diverge between implementations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: `count_non_security()` has unclear public API status
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The public `count_non_security()` wrapper is only used by `ship.py`, so leaving it exported invites drift from the private helper unless it is documented as supported surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Scoped `oos-pipeline` load-directive tests use fragile 8-line awk windows
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Structure tests depend on fixed proximity windows in `SKILL.md`; harmless edits can move mandatory lines outside the window and cause false failures while broader directive counts still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Non-security OOS counting is duplicated in checkpoint/gate scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Existing duplicate non-security counting logic between the checkpoint and gate awk means security predicate changes require multiple coordinated edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Bash `pr-create` resume re-arms `OOS_PENDING` from non-empty accepted files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt, dyn-python-ship-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: Resuming with `--resume-phase pr-create` routes through `pr-prep`, which sets `OOS_PENDING=true` on any non-empty accepted-OOS markdown before honoring completed disposition evidence. After Step 9a.1 clears `OOS_PENDING`, the run can loop forever instead of opening the PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-oos-flow-output.txt: Address the concern above.
  - From dyn-python-ship-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Manifest security routing can be spoofed, injected, or miss sensitive items
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-oos-flow-output.txt, dyn-redaction-boundary-output.txt
- **Severity**: important
- **Concern**: `materialize-manifest-oos.sh` security routing relies on inconsistent text/markdown heuristics around `focus_area` and description bodies. A malformed or adversarial manifest can privately route non-security items, misclassify via newline injection, or send unmarked security narratives to the public OOS path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-oos-flow-output.txt: Address the concern above.
  - From dyn-redaction-boundary-output.txt: Address the concern above.

### FINDING_11: Python `disposition_ok` is stricter than the bash gate for inline-triage-only evidence
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: Python returns failure when non-security OOS exists and `oos-issues.ndjson` is missing before checking inline triage/sentinel evidence, while the bash gate can pass from filed-URL evidence alone. Direct callers can get different outcomes from the same tree state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Security OOS sidecar handling is inconsistent or underdocumented
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-redaction-boundary-output.txt
- **Severity**: important
- **Concern**: `security-oos-observations.md` blocking/remediation is implemented across ship/checkpoint/Python paths but not fully documented in the OOS pipeline, not enforced inside Python `_oos_gate`, and has fork/checkpoint semantics that can diverge from `ship-pr`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-redaction-boundary-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Python ship re-handoffs after completed OOS disposition on accepted markdown
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-oos-flow-output.txt, dyn-python-ship-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` returns `NEEDS_USER_OOS_FILING` on any non-empty accepted-OOS markdown before consulting `_oos_gate` disposition evidence. Post-Step 9a.1 reinvocation can therefore loop instead of reaching `ensure_pr`, and security-only accepted content can be treated as needing public filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-oos-flow-output.txt: Address the concern above.
  - From dyn-python-ship-output.txt: Address the concern above.

### FINDING_14: Materialized OOS markdown append is not atomic
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Incremental append in `materialize-manifest-oos.sh` can leave partial accepted-OOS markdown if the process is interrupted mid-loop, confusing later combine/gate steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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
