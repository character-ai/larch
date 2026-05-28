### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:419-444
- **Concern**: Plan pins the new audit docs but omits the required SKILL.md args-contract pin. Scenario: Decision 2 requires structural assertions that the Step 0 dirty-tree recovery section retains sentinel env and args contract; existing checks cover sentinel/env/preflight but would still pass if the resume call dropped --caller-env --forked-target --upstream-repo or --run-id propagation
- **Proposed resolution**: Add one simple literal grep/read assertion for the complete --resume-plan-tail invocation, or count that _ib_caller_env _ib_issue _ib_fork _ib_run_id and _ib_preflight expansions appear in both bootstrap calls

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:792-910
- **Concern**: Plan says it will enumerate each helper after the checkpoint but leaves out redaction/error/breadcrumb helpers. Scenario: The proposed audit can claim complete helper idempotency while omitting redact-secrets.sh, redact-tmpdir-paths.sh, append-tool-failure.sh failure paths, and emit_plan_materialize_breadcrumbs_if_enabled; these are still post-checkpoint helper calls under the audited line range
- **Proposed resolution**: Add a short aggregate audit bullet for the redaction helpers, append-tool-failure.sh failure-only appends, and breadcrumb emitter, noting they are safe on the canonical first-bail flow and which ones are not independently idempotent if forced to re-run
