### FINDING_2: `test-bug-structure.sh` missing lint/doc registration
- **Reviewer(s)**: Cursor-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds `scripts/test-bug-structure.sh` and Makefile wiring but omits repo conventions for Makefile-only harnesses: `agent-lint.toml` allowlist entry and sibling `scripts/test-bug-structure.md`. Peer harnesses (`test-alias-structure.sh`, etc.) follow this pattern; as planned, `make lint` or the script-doc invariant can fail after the harness lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `scripts/test-bug-structure.sh` (and optional sibling `scripts/test-bug-structure.md` per repo convention) to the Makefile-only allowlist block in `agent-lint.toml`, matching `test-alias-structure.sh`
  - From Codex-Requirements: Add ### NEW: scripts/test-bug-structure.md and ### UPDATED: agent-lint.toml entries for the new harness and sibling, following the scripts/test-alias-structure.sh pattern


### FINDING_3: Diagram failure detail not durable in committed run logs
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: Item 3 enriches the failure `reason` with a tmpdir log path, but Step 18 cleanup removes `$IMPLEMENT_TMPDIR`. The committed run log still lacks redacted stderr/stdout or other diagnosable cause after success, so operators cannot distinguish timeout, auth/quota, or crash post hoc.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Return a short one-line redacted stderr/stdout tail in the reason that Step 7a commits, or copy the redacted failure log into the committed larch-log run directory before cleanup.
  - From Codex-Pragmatic: Make the durable execution-issues record include a capped redacted stderr/stdout tail or append the redacted failure body via the existing execution-issues failure path. Keep the tmpdir log optional, but do not rely on its path as the durable diagnostic.


### FINDING_4: `DIAGRAM_REASON` omitted on Step 7a rebase-failure early return
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan threads `DIAGRAM_REASON` through the happy-path KV emit block but not the rebase-checkpoint early return (`probe.returncode != 0` at ~292–297). When diagram generation fails and 7a.r rebase exits non-zero, orchestrator gets `DIAGRAM_STATUS=failed` without `DIAGRAM_REASON` even though `_append_diagram_warning` may carry enriched detail in execution-issues; machine consumers miss exit code and failure-log path on that branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Emit DIAGRAM_REASON on the probe.returncode != 0 branch (lines 291-298) using the same diagram_reason variable as the success path
  - From Cursor-Requirements: Add diagram_reason capture on failure and emit DIAGRAM_REASON= on both terminal KV paths (rebase-failure return at 292-297 and the normal return at 310-315); extend test_step_7a.py with a rebase-failure + diagram-failure case asserting DIAGRAM_REASON is present



