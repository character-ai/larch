### OOS_1: [OUT_OF_SCOPE] scan_file silently returns no findings on SyntaxError or OSError
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `scan_file` silently returns `[]` on `SyntaxError` or `OSError`. A file with a syntax error containing upward imports is treated as clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Fail closed or emit a warning on parse/read failure instead of returning [].

### OOS_2: [OUT_OF_SCOPE] CLI importlib string dispatch is outside AST layering scope
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: CLI uses importlib string dispatch; AST layering cannot trace those edges. Dynamic imports through the registry are outside static analysis scope. Pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Pre-existing; document as a known CLI-layer exception if needed.

### OOS_3: [OUT_OF_SCOPE] scan_file silent failure matches sibling ratchet behavior
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `scan_file` silently returns `[]` on `OSError` or `SyntaxError`. Matches sibling ratchet behavior; syntax issues are caught by ruff/pylint in the same py-lint pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Optionally emit stderr warnings; consistent with existing ratchets not required for this feature

### OOS_4: [OUT_OF_SCOPE] Dynamic imports via importlib are not analyzed
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Dynamic imports via importlib are not analyzed. Runtime import paths can bypass layering like other AST-only ratchets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document limitation or add separate dynamic analysis if required later

### OOS_5: [OUT_OF_SCOPE] PACKAGE_TIER must be manually updated for new subpackages
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `PACKAGE_TIER` must be manually updated for new subpackages; `from larch import` resolution stays wrong until the dict is edited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document new-package checklist or derive tiers mechanically

### OOS_6: [OUT_OF_SCOPE] Missing parity tests for duplicate-live, malformed baseline, and relocation-aware --write
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Missing parity tests for duplicate-live exit 2, malformed baseline exit 2, and relocation-aware `--write` reason preservation that sibling ratchet test files cover. A future edit to `_records_for_write` or `_check_duplicate_live` could break `make regen-layering-baseline` or silently mishandle moved modules while py-test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Port relocation and duplicate-live main() tests from test_lint_subprocess_via_runner.py / test_lint_env_via_config_constant.py.

### OOS_7: [OUT_OF_SCOPE] scan_file tests omit import larch.<pkg> and from larch import <pkg> paths
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `scan_file` tests cover only `from`-import violation shapes; `import larch.<pkg>` and `from larch import <pkg>` paths in `_importee_packages` are untested. A regression in `ast.Import` handling could let upward imports using those forms slip past the ratchet undetected by py-test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add parametrized scan_file cases for import larch.state and from larch import state in a tier-1 module.

### OOS_8: [OUT_OF_SCOPE] relevant-checks py-lint trigger misses python/larch/** edits in isolation
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `relevant-checks` py-lint trigger matches `python/*.py` top-level only, not `python/larch/**` edits in isolation. Implement sessions that touch only nested larch modules may skip local py-lint until CI, delaying ratchet regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend _DIRECT_TARGET_RULES with a python/larch/**/*.py wants_py_lint rule or explicit lint-module mapping.

