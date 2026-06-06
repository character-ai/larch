### FINDING_1: Validation Codex launcher example omits required output/timeout flags
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-collector-contracts, Cursor-Requirements, Codex-Requirements, Cursor-dyn-doc-contract-drift
- **Severity**: important
- **Concern**: The validation-phase `launch-codex-exec.sh` example omits required `--output` and `--timeout` flags, so the launcher can fail argument validation or produce output/sidecars at paths that the unchanged collection step does not read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-collector-contracts: Add --output "$RESEARCH_TMPDIR/codex-validation-output.txt" --timeout 1800 to the validation-lane launch-codex-exec.sh example, matching research-phase.md and the unchanged COLLECT_ARGS path
  - From Cursor-Requirements: Launcher arg validation fails or writes sidecars to the wrong stem; validation collection never sees the expected sentinel path Add `--output "$RESEARCH_TMPDIR/codex-validation-output.txt" --timeout 1800` to the validation-lane `launch-codex-exec.sh` invocation (matching research-phase and the unchanged COLLECT_ARGS path)
  - From Codex-Requirements: Add --output "$RESEARCH_TMPDIR/codex-validation-output.txt" --timeout 1800 to the validation-phase replacement command
  - From Cursor-dyn-doc-contract-drift: Add --output "$RESEARCH_TMPDIR/codex-validation-output.txt" --timeout 1800 to the validation-phase launch-codex-exec.sh example (mirror research-phase.md).


### FINDING_3: Negotiation Codex temp home lacks cleanup
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-dyn-auth-surface-sweep
- **Severity**: important
- **Concern**: The planned Codex auth path in `run-negotiation-round.sh` creates a temporary `CODEX_HOME` with copied config and/or auth material but does not specify cleanup on every success and failure path, risking leaked auth-related filesystem state under `/tmp`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add branch-local cleanup for codex_home on all codex paths and assert removal in test-run-negotiation-round.sh
  - From Codex-Edge: Add branch-local cleanup/trap immediately after mktemp -d and remove the temp CODEX_HOME on success, auth-prep failure, model-args failure, and codex exec failure, mirroring check-reviewers.sh cleanup behavior
  - From Codex-Innovation: Add a branch-local cleanup trap or cleanup function immediately after mktemp -d, and clear it only after rm -rf succeeds on every codex branch exit path.
  - From Codex-Pragmatic: Add a branch-local cleanup trap or explicit cleanup that removes the temp CODEX_HOME on every codex-branch exit path
  - From Codex-dyn-auth-surface-sweep: Add a codex branch cleanup trap/helper for codex_home and copied config, mirroring check-reviewers.sh cleanup paths before returning or exiting


### FINDING_4: Collector retry does not replay Codex auth setup
- **Reviewer(s)**: Codex-dyn-auth-surface-sweep
- **Severity**: important
- **Concern**: The collect-managed retry path replays only `CMD_JSON` argv and not `CODEX_HOME` or auth preparation state, so login fallback retries can lose stripped-home/auth-symlink setup or read ambient stale config.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-auth-surface-sweep: Add retry through launch-codex-exec outer metadata and collector allowlisting, or otherwise disable/qualify collector retry for this launcher until login fallback is replayed through external_prepare_codex_auth


### FINDING_5: Skill fences use relative launcher path instead of plugin root
- **Reviewer(s)**: Cursor-dyn-collector-contracts
- **Severity**: important
- **Concern**: Planned skill reference fences call bare `scripts/launch-codex-exec.sh`, which can resolve against the consumer repository cwd instead of the plugin tree, breaking `/research` and `/design` orchestration launches and downstream collection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-collector-contracts: Use the same ${CLAUDE_PLUGIN_ROOT}/scripts/launch-codex-exec.sh prefix as today's run-external-agent.sh fences in all four reference updates


### FINDING_6: Structural test would wrongly forbid Cursor path’s run-external-agent usage
- **Reviewer(s)**: Codex-dyn-collector-contracts
- **Severity**: important
- **Concern**: The proposed structural test appears to require `run-external-agent.sh` only inside `launch-codex-exec.sh`, but `lint-fix-loop.sh` still legitimately uses `run-external-agent.sh` for `run_cursor`, so the test would fail or force an unrelated Cursor refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-collector-contracts: Narrow the structural pin to the Codex branch/run_codex routing: require launch-codex-exec.sh for Codex, while still allowing lint-fix-loop.sh to reference run-external-agent.sh for run_cursor.


### FINDING_7: Research docs retain stale “Codex unmeasurable” telemetry prose
- **Reviewer(s)**: Codex-dyn-doc-contract-drift
- **Severity**: important
- **Concern**: The plan adds Codex launcher usage recording but leaves research-phase prose saying external non-fallback Codex lanes are unmeasurable, creating a documentation/behavior mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-doc-contract-drift: In the planned update to research-phase.md, revise line 135 to say Claude fallbacks write token-tally sidecars and Codex lanes get best-effort launcher usage records, or drop the unmeasurable sentence if no per-lane tally is promised.


### FINDING_8: Helper sibling contract inventory omits newly wired users
- **Reviewer(s)**: Codex-dyn-doc-contract-drift
- **Severity**: important
- **Concern**: The plan updates auth helper users but does not update `scripts/lib-external-launcher-common.md`’s sibling contract inventory to include new `launch-codex-exec.sh`, `run-negotiation-round.sh`, and usage-recording call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-doc-contract-drift: Add scripts/lib-external-launcher-common.md to the UPDATED list and refresh the wired-call-site and usage-scraper bullets with the same merged inventory, or point them to the canonical docs if avoiding duplicate lists.


