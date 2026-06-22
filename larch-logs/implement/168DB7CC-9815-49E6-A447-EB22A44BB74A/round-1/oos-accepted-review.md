### OOS_1: [OUT_OF_SCOPE] Bulk mode symlink escape via `impl_root.iterdir()`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Bulk mode (no `--run-dir`) still iterates `impl_root.iterdir()` without resolving or re-checking each entry, so a symlinked child directory pointing outside `larch-logs/implement/` could still be processed destructively. Pre-existing; this PR only guards the `--run-dir` path.
- **Suggested revisions (informational for voters; coder decides)**:


