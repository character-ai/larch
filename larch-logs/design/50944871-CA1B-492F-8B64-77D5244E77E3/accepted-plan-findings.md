### FINDING_1: Collector failure log deny patterns target wrong filenames
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Codex-dyn-glob-safety, Codex-dyn-fixture-parity, Codex-dyn-producer-name-audit
- **Severity**: important
- **Concern**: Collector failure logs are produced from manifest slot names, not output-family basenames. Denylist/test plans that target names such as `codex-primary-plan-*-collector.failure.log` can miss real files like `codex-plan-*-collector.failure.log`, `dyn-codex-plan-*-collector.failure.log`, `dyn-cursor-plan-*-collector.failure.log`, and `unknown-slot-collector.failure.log`, allowing transcript/stderr-bearing diagnostics to be published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add deny arms and fixtures for the real slot-name failure logs: codex-plan-*-collector.failure.log, dyn-cursor-plan-*-collector.failure.log, dyn-codex-plan-*-collector.failure.log, plus the existing cursor, claude, and unknown-slot cases
  - From Cursor-Edge: Anchor exclusions on slot names from plan-review-loop.sh (codex-plan-*-collector.failure.log, dyn-cursor-plan-*-collector.failure.log, dyn-codex-plan-*-collector.failure.log, cursor-plan-*-collector.failure.log, claude-plan-*-collector.failure.log, unknown-slot-collector.failure.log) or a single *-collector.failure.log arm with a sole-producer comment; drop codex-primary-plan-*-collector.failure.log; pin fixtures to real committed basenames not codex-primary-plan-*-collector.failure.log
  - From Codex-Edge: Add deny/test fixtures for the real slot-name log basenames: codex-plan-*-collector.failure.log, dyn-cursor-plan-*-collector.failure.log, dyn-codex-plan-*-collector.failure.log, plus the existing unknown-slot pattern; keep codex-primary collector logs only if a real producer uses them.
  - From Cursor-Pragmatic: Add codex-plan-*-collector.failure.log dyn-codex-plan-*-collector.failure.log dyn-cursor-plan-*-collector.failure.log and unknown-slot-collector.failure.log (or a single *-collector.failure.log arm — only plan-review-loop.sh emits these) to design_artifact_excluded; drop the codex-primary-plan-*-collector.failure.log arm; fixture codex-plan-arch-collector.failure.log and dyn-codex-plan-harness-fidelity-collector.failure.log in the deny-loop
  - From Codex-Pragmatic, Codex-Requirements: Add deny/test coverage for real slot-derived collector logs: `codex-plan-*-collector.failure.log`, `dyn-codex-plan-*-collector.failure.log`, `dyn-cursor-plan-*-collector.failure.log`, plus the already planned unknown/generic cases
  - From Codex-dyn-glob-safety: Use the real collector-failure glob arms codex-plan-*-collector.failure.log and dyn-codex-plan-*-collector.failure.log, and fixture those exact basenames; keep codex-primary only if a real producer is identified.
  - From Codex-dyn-fixture-parity: Add deny arms and assert_excluded loop entries for the actual slot-slug collector names: codex-plan-*-collector.failure.log, dyn-cursor-plan-*-collector.failure.log, dyn-codex-plan-*-collector.failure.log, and unknown-slot-collector.failure.log; keep codex-primary/claude collector patterns only if a producer is verified
  - From Codex-dyn-producer-name-audit: The plan should use slot-derived collector failure deny/test names: cursor-plan-*-collector.failure.log, codex-plan-*-collector.failure.log, dyn-cursor-plan-*-collector.failure.log, dyn-codex-plan-*-collector.failure.log, and unknown-slot-collector.failure.log. Remove codex-primary-plan-* and claude-plan-* collector failure fixtures unless a producer is added.


### FINDING_2: Aggregate plan-review collector stderr remains publishable
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan excludes per-slot collector failure logs but omits the aggregate `plan-review-collector.stderr`, which can contain failed-agent stderr tails or launcher/validator diagnostics and would still be committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the exact basename plan-review-collector.stderr to design_artifact_excluded and cover it in scripts/test-design-log-publish.sh plus the synced docs/security note
  - From Codex-Pragmatic: Add an exact `plan-review-collector.stderr` exclusion to `design_artifact_excluded()` with matching test and doc updates, or explicitly justify keeping it as a canonical published artifact


