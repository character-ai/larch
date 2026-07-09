# Review Round 1

- Mode: `diff`
- 3 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_6: missing regression test for the `run_logs` / `run_log_flush` shape
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The tests do not cover the plan-required `run_logs` / `run_log_flush` / `_commit_run` regression shape, so a real-module resolution bug could slip through while synthetic fixtures still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: `Add a fixture using larch.report.run_logs and run_log_flush asserting facade flag + defining-module non-flag.`


### FINDING_13: filesystem fallback resolves unbound package children
- **Reviewer(s)**: codex-specialist-testing, dyn-dyn-static-resolver
- **Severity**: major
- **Concern**: The resolver falls through to on-disk submodules even when the parent never imports or re-exports them, which can flag valid package-child monkeypatches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: `Remove the fallback and only resolve a chain step when the parent module source statically binds that attribute; add a regression test for the unbound package-child case.`
  - From dyn-dyn-static-resolver: `Drop the filesystem fallback (return None after _imported_module_attribute fails), or gate it on an explicit import/submodule binding in the parent AST, matching _module_ref_from_from_import; add a fixture where a submodule file exists but the parent never imports it and assert the chain is skipped.`


### FINDING_14: duplicate module-level imports resolve inconsistently
- **Reviewer(s)**: dyn-dyn-static-resolver
- **Severity**: major
- **Concern**: Duplicate module-level imports of the same name are handled inconsistently, so chain resolution and defining-module reporting can disagree after a refactor adds a second import for the same alias.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-static-resolver: `Use one policy everywhere (last binding matches runtime), ideally a shared helper that scans tree.body in source order and returns the final import binding for a name; cover it with a facade fixture that imports the same alias twice.`


