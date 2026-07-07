### [rejected] FINDING_1

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_1: skip-approve docs omit strong-audit Gate C exception
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: minor
- **Concern**: Public documentation for `/design --skip-approve` still promises unconditional Gate C auto-approval in `README.md`, `docs/skills.md`, `docs/workflow-lifecycle.md`, and `skills/design/references/flags.md`. Users and operators may expect no final Gate C prompt, but strong accepted-findings audit dissent now forces Gate C approval. Update those plan-named docs and the flag reference to state that the audit still runs and strong dissent forces Gate C approval; consider adding a structural doc-sync check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0

