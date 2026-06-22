### OOS_4: [OUT_OF_SCOPE] Full implementation diff emitted on CLI stdout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `materialize_diff_main()` prints the full branch diff on stdout. Large implementations can blow orchestrator context during Phase A materialize-diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Omit diff from stdout; keep tmpdir artifact only


