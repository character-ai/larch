### [Plan Review] FINDING_6

### FINDING_6: NEVER #17/#18 prose can drift from the checkpoint entrypoint
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: latent
- **Concern**: The plan keeps NEVER #17/#18 wording even though #18 still names direct `oos-disposition-gate.sh` invocation as the required Step 8+ action. After extraction, maintainers may bypass the checkpoint helper’s input plumbing and logging, weakening the load-bearing invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-matrix: Minimally update NEVER #17/#18 to say the Step 8+ checkpoint helper invokes the gate and owns gate failure logging, while preserving the OOS_PENDING and run-statistics invariants

