### [Plan Review] FINDING_3

### FINDING_3: Publish tests do not assert voting-tally.md remains staged
- **Reviewer(s)**: Codex-dyn-fixture-parity
- **Severity**: latent
- **Concern**: The planned publish tests preserve findings and voter-output artifacts but do not add an end-to-end positive assertion that canonical `voting-tally.md` is still published, so a staging regression could pass tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-fixture-parity: Add a minimal scripts/test-design-log-publish.sh fixture under plan-review/round-1/voting-tally.md and assert it appears in larch-logs/design/RUNPUB1/plan-review/round-1/voting-tally.md alongside findings.md


### [Plan Review] FINDING_4

### FINDING_4: Planned Cursor/Codex .stderr exclusions may target unproduced artifacts
- **Reviewer(s)**: Codex-dyn-producer-name-audit
- **Severity**: nit
- **Concern**: The plan adds Cursor/Codex `.stderr` exclusions and fixtures, but current producers appear to write those stderr-like diagnostics to other suffixes such as `.sidecar`, `.diag`, `.launch-stderr`, or `.stderr-tail`; only Claude writes `${OUTPUT}.stderr`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-producer-name-audit: Drop Cursor/Codex .stderr deny arms and fixtures, or cite a real producer before adding them. Keep Claude .stderr plus the existing Cursor/Codex .sidecar, .diag, .launch-stderr, and .stderr-tail coverage.

