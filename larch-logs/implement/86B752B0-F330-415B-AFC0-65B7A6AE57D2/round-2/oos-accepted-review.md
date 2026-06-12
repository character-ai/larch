### OOS_3: [OUT_OF_SCOPE] ci_monitor lacks ledger fields for additional handoff tokens
- **Reviewer(s)**: dyn-ledger-chain-output.txt
- **Severity**: latent
- **Concern**: `python/ci_monitor.py` has no `ledger_*` usage. Plan items requiring full ledger-ready data for `first-fixer-non-health` and `local-unfixable` still need enrichment in `ci_monitor.py` or at the `run_ship` call site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ledger-chain-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] Legacy report renderers remain callable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Legacy `bug-body`, `bug-comment`, and issue-input renderers remain reachable. A stale caller can produce removed surfaces or enum-only stall titles instead of root-caused reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


