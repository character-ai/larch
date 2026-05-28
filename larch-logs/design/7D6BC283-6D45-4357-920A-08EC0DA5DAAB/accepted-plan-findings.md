### FINDING_1: Missing args-contract assertion in structural tests
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan pins new audit docs but omits the required `SKILL.md` args-contract pin, so tests could pass even if the resume call dropped `--caller-env`, `--forked-target`, `--upstream-repo`, or `--run-id` propagation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Add one simple literal grep/read assertion for the complete --resume-plan-tail invocation, or count that _ib_caller_env _ib_issue _ib_fork _ib_run_id and _ib_preflight expansions appear in both bootstrap calls


### FINDING_2: Post-checkpoint helper audit omits helper classes
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: latent
- **Concern**: The planned audit claims helper idempotency coverage but leaves out redaction helpers, failure-only append paths, and breadcrumb emission under the audited post-checkpoint range.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Add a short aggregate audit bullet for the redaction helpers, append-tool-failure.sh failure-only appends, and breadcrumb emitter, noting they are safe on the canonical first-bail flow and which ones are not independently idempotent if forced to re-run

