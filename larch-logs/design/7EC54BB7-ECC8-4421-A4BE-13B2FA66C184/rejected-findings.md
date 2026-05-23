### [Plan Review] FINDING_11

### FINDING_11: Shared atomic-write helper across three dispatchers
- **Concern**: The plan creates three near-identical atomic-write + `emit_kv` sequences across `dispatch-with-waterfall.sh`, `dispatch-plan-voters.sh`, and `dispatch-code-voters.sh` without a shared helper. Behavior drift on error handling, tempdir choice, or chmod becomes likely over time.
- **Reviewers**: Cursor-arch, Codex-innovation
- **Severity**: nit / architecture
- **Focus area**: architecture
- **Suggested resolution**: Add an optional small sourced helper (e.g., `write_paths_file_atomic` in `scripts/lib-quiet.sh` or a tiny `scripts/lib-paths-file.sh`) and reuse from all three dispatchers.


### [Plan Review] FINDING_13

### FINDING_13: VOTER_PATHS_FILE in voter dispatchers is scope creep
- **Concern**: Plan adds `VOTER_PATHS_FILE` to both voter dispatchers even though the plan itself notes voter dispatchers don't have the multi-path hazard (single-path `VOTER_N_PATH` KVs are safe). Broadens runtime API, docs, and harness surface without an existing consumer.
- **Reviewers**: Cursor-pragmatic
- **Severity**: nit
- **Focus area**: architecture (scope creep)
- **Suggested resolution**: Optionally limit the change to `dispatch-with-waterfall.sh` + `collect-agent-results.sh` + design Step 3. Voter dispatcher uniformity is documentation, not necessity; defer until a consumer materializes. *Note*: Round 1 user choice was "all three dispatchers" for uniform symmetry, so this finding is in scope-creep tension with an explicit user decision.


