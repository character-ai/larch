### OOS_1: [OUT_OF_SCOPE] direct shell stall exit semantics diverge from the Python dispatcher
- **Reviewer(s)**: codex-specialist-correctness, dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: The direct shell `--ready-to-commit` path still exits 1 on `NEXT_ACTION=stall` while the Python dispatcher returns 0 for the same routed stall, so stall callers can observe inconsistent semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: If a future chunk reuses direct shell --ready-to-commit, align its routed-stall rc with python/larch/implement/dispatch_commit_route.py:934-948.
  - From dyn-dyn-bgjob-flow: Address the concern above.


