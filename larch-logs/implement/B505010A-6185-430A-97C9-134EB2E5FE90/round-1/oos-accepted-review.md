### OOS_1: [OUT_OF_SCOPE] Run-scoped writes still need fully fd-pinned parent-chain handling
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: The run-scoped activation and breadcrumb writes still rely on separate symlink checks plus full-path opens, so a same-UID swap in the parent chain can redirect `activate_run()` or `append_breadcrumb_for_run()` outside `progress_root`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: "Open the parent chain with fd-relative APIs and keep the verified directory fd through the final write"
  - From codex-specialist-edge-cases: "Anchor the create/open sequence on a trusted directory fd and use fd-relative directory creation and open, or otherwise make verification atomic with the operation."
  - From cursor-specialist-edge-cases: "if you want to close this class-wide, hold a verified parent dir fd through mkdir and leaf open, not only on the final write."


