### OOS_1: Post-rebase compose gate refresh missing
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing, dyn-dyn-compose-gate
- **Severity**: important
- **Concern**: After in-driver rebases that change HEAD, the ship loop resumes without re-running the compose gate or refreshing the PR body, so the PR can continue with stale guidelines text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Exit for guidelines-assessment or run _guidelines_gate_before_pr and ensure_pr body refresh after in-driver rebases.
  - From codex-specialist-testing: Add a post-rebase compose-gate and PR body update path before CI or merge continues, plus regression coverage.
  - From dyn-dyn-compose-gate: After any in-driver rebase that changes HEAD, route through the same compose gate used at pre-PR compose (request guidelines-assessment when needed, or refresh and call update_pr_body when a consumable note exists) before continuing CI/merge.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
