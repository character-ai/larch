# Review Round 3

- Mode: `diff`
- 12 accepted, 12 rejected (11 exonerated)

## Accepted Findings

### FINDING_1: Security-routed manifest OOS can clear `OOS_PENDING` without a durable private disposition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-log-evidence-output.txt, dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: Manifest-only security OOS are written to `security-oos-observations.md` and set `OOS_PENDING=true`, but the canonical Step 9a.1 flow reads only accepted `### OOS_` markdown. With zero non-security accepted blocks, the pipeline can take the no-input/all-clear path and clear `OOS_PENDING` without SECURITY.md private-disclosure handling, NDJSON evidence, or a documented disposition for the security sidecar. The sidecar is also not clearly documented as a private, never-filed surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-log-evidence-output.txt, dyn-public-redaction-output.txt: Address the concern above.


### FINDING_10: Python NDJSON discovery diverges from checkpoint/run-id resolution
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-python-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python `_oos_gate` uses a different NDJSON discovery order than the checkpoint path. It can fall back to foreign NDJSON when a keyed batch is missing, or miss the session-id keyed batch when `RUN_ID` is unset, producing bash/Python disposition divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-python-bash-parity-output.txt: Address the concern above.


### FINDING_11: Python accepted-OOS flow can bypass mandatory Step 9a.1 handoff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bash-state-output.txt, dyn-python-bash-parity-output.txt
- **Severity**: important
- **Concern**: The Python ship path goes from materialization to `disposition_ok()` without mirroring bash’s non-empty accepted-OOS size gate. Non-empty main/design/review accepted OOS can proceed to PR creation when disposition evidence appears sufficient, bypassing the orchestrator Step 9a.1 handoff and related NDJSON/checkpoint work. Tests also miss a negative design-export-only blocking case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-bash-state-output.txt, dyn-python-bash-parity-output.txt: Address the concern above.


### FINDING_14: Materializer failure with non-empty manifest can leave no accepted OOS to file
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: If `materialize-manifest-oos.sh` fails while manifest `oos_observations[]` is non-empty, the flow can set `OOS_PENDING=true` but produce no accepted markdown. Step 9a.1 may then treat the batch as no-input and clear disposition without ever filing the manifest OOS. The test harness does not assert this fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-bash-state-output.txt: Address the concern above.


### FINDING_18: Non-array `oos_observations` is silently treated as empty
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `oos_observations` exists but is not a JSON array, the helper can compute length zero and exit successfully, causing manifest OOS content to be dropped instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: Resume directly to `pr-create` skips re-materialization
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: `--resume-phase pr-create` jumps past `run_pr_prep_phase` and does not rerun manifest materialization. If `OOS_PENDING` was falsely cleared after a materializer failure, resume can open the PR without ever regenerating accepted OOS markdown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.


### FINDING_2: Manifest security routing predicate diverges from the gate and contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-manifest-materializer-output.txt, dyn-log-evidence-output.txt, dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: `materialize-manifest-oos.sh` security-routes observations on title-prefix and/or JSON `focus_area`, while the documented Step 9a.1/gate-aligned rule focuses on dedicated `- **focus-area**:` lines. A non-security item titled like “Security …” can be diverted to the private sidecar and never filed publicly, while docs/tests/contracts describe a different predicate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-manifest-materializer-output.txt, dyn-log-evidence-output.txt, dyn-public-redaction-output.txt: Address the concern above.


### FINDING_20: Step 2 manifest sanitization drops structured `focus_area`
- **Reviewer(s)**: dyn-manifest-materializer-output.txt
- **Severity**: important
- **Concern**: Step 2 rebuilds manifest OOS entries with only title, description, and phase before materialization, dropping `focus_area` / `focus-area`. Security-only structured JSON markers can be lost, causing security observations to be materialized as non-security public OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-materializer-output.txt: Address the concern above.


### FINDING_24: All-already-filed path can pass without committed NDJSON evidence
- **Reviewer(s)**: dyn-log-evidence-output.txt
- **Severity**: important
- **Concern**: The documented all-already-filed branch requires step 6 NDJSON evidence, but the mechanical gate can pass on strict filed URL lines alone. An orchestrator can skip NDJSON materialization and still clear `OOS_PENDING`, breaking the larch-log evidence contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-evidence-output.txt: Address the concern above.


### FINDING_27: Prompt-side sanitize requirements lack mechanical enforcement before combine/issue
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: OOS pipeline steps require prompt-side sanitization before composing combined/grouping files and issue bodies, but no script enforces it at those boundaries. Manifest-derived session text can propagate to public issues or committed logs if the orchestrator misses the manual sanitize step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.


### FINDING_28: Ship-pr structure guard can pass on path assignment without materializer invocation
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: latent
- **Concern**: The ordering guard matches the `materialize-manifest-oos.sh` path assignment rather than the actual `bash "$materialize_oos"` invocation. Deleting the call while leaving the assignment/comment could still satisfy CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.


### FINDING_6: Manifest public-text sanitization is duplicated and incomplete for public-boundary data
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: `sanitize_public_text` duplicates redaction rules instead of using a shared outbound sanitizer, and its internal URL/token coverage is narrower than the public-boundary risk. Manifest-derived title/body text can reach accepted OOS markdown, public issues, or logs with missed internal hosts or secret-like values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-public-redaction-output.txt: Address the concern above.


