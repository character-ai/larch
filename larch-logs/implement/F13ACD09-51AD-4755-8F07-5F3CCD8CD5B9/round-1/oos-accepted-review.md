### OOS_1: [OUT_OF_SCOPE] Inner run-dir escape symlinks not guarded during `rglob`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Symlinks inside a legitimate run directory that point outside `impl_root` are not guarded during `rglob`-based deletes. Destructive cleanup can follow nested escape symlinks and delete external files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use follow_symlinks=False on glob/rglob or check containment on each matched path before delete.
  - From cursor-specialist-edge-cases: Mirror gc_run_logs.py: add per-path containment checks or use os.walk(followlinks=False) before unlink/rmtree.


### OOS_2: [OUT_OF_SCOPE] Contract doc omits bulk-mode containment guard
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The contract documents `--run-dir` containment but not the bulk-mode guard. Operators reading only the contract may assume bulk mode lacks the symlink/`..` guard that `--run-dir` has.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add a bulk-mode containment invariant parallel to the --run-dir bullet.
  - From cursor-specialist-edge-cases: Add a bulk-mode invariant bullet documenting skip-on-escape behavior.
  - From cursor-specialist-testing: Add a bullet that bulk enumeration applies the same resolved-path containment check and skips entries that would escape `larch-logs/implement/`.


### OOS_3: [OUT_OF_SCOPE] `consolidate_breadcrumbs()` follows nested breadcrumbs symlink outside run dir
- **Reviewer(s)**: codex-specialist-testing, dyn-dyn-bulk-symlink-containment-codex
- **Severity**: latent
- **Concern**: `consolidate_breadcrumbs()` still follows a `breadcrumbs` directory symlink inside an otherwise valid run directory. A run dir with `breadcrumbs` symlinked outside can create `quiet.log` and unlink `larch-quiet-*.log` files outside the implement log tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add a per-run safety guard before destructive path operations. Reject or skip cleanup roots whose resolved paths are outside the resolved run directory, and add a regression test for a nested symlinked breadcrumbs directory.
  - From dyn-dyn-bulk-symlink-containment-codex: Reject symlinked child directories before write/delete operations, or walk run dirs with a no-follow policy and validate each destructive target.

**Subsumption note:** Input FINDING_9 (bulk listing unresolved paths, `[OUT_OF_SCOPE]` from cursor-specialist-edge-cases) was merged into FINDING_1 as the same behavioral risk; cursor-specialist-edge-cases is omitted from the in-scope block because that source finding was exclusively `[OUT_OF_SCOPE]`.


