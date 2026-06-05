### FINDING_2: Missing regression for dynamic Codex `.events.jsonl` denial
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan requires dynamic Codex `.events.jsonl` files to remain denied, but planned negative tests only cover prompt sidecars, so an implementation could accidentally admit raw telemetry while still passing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add one dynamic Codex `.events.jsonl` fixture and `assert_not_file` check in `scripts/test-larch-log-write-round.sh`, alongside the planned prompt-sidecar negative.


### FINDING_3: Harness documentation update should be mandatory
- **Reviewer(s)**: Cursor-dyn-doc-sync
- **Severity**: important
- **Concern**: The companion harness doc update is optional even though the contract changes add phased dynamic Codex, cap-hit, and prompt-negative coverage; implementers may skip documenting rules that then exist only in shell tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-doc-sync: Add an explicit ### UPDATED: scripts/test-larch-log-write-round.md step listing phased dynamic Codex, cap-hit, and prompt-exclusion bullets (drop the “only if summaries name” gate for this file)


### FINDING_4: Conditional doc-sync note references missing companion doc
- **Reviewer(s)**: Codex-dyn-doc-sync
- **Severity**: nit
- **Concern**: The plan conditionally references a companion doc that does not exist, which could cause implementers to create unnecessary documentation or waste time searching for a missing target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-doc-sync: Revise the note to mention only existing companion docs: keep conditional sync for `scripts/test-larch-log-write-round.md` if its summary changes, and rely on `scripts/test-lib-design-round-artifacts.sh` plus `scripts/lib-design-round-artifacts.md` for the design-round artifact contract

