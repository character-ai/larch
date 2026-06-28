# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: _importer_package maps larch/__init__.py to larch.__init__ instead of tier-0 larch
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: `_importer_package` maps `larch/__init__.py` to `larch.__init__` (default tier 2) instead of `larch` (tier 0). Adding `from larch.state import session_env` to `larch/__init__.py` is an upward tier-0→tier-2 violation, but lint exits 0 because both sides are treated as tier 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Map larch/__init__.py to package larch at tier 0; keep nested __init__.py on the subpackage path rule.


### FINDING_2: from larch import <name> falls back to tier-0 larch for unknown subpackages
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `from larch import <name>` falls back to importee `larch` (tier 0) when `larch.<name>` is not in `PACKAGE_TIER`. A `larch/core/foo.py` file with `from larch import newpkg` before `newpkg` is in `PACKAGE_TIER` bypasses the core→domain upward check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Always resolve to larch.{alias.name} and use _package_tier (unknown → tier 2); remove the else pkgs.append("larch") branch.
  - From cursor-specialist-edge-cases: Always record importee as larch.{alias.name} and use _package_tier(); add test for unlisted subpackage via barrel import


### FINDING_3: Relative ImportFrom nodes are skipped, allowing upward-import bypass
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, codex-generalist
- **Severity**: important
- **Concern**: `_importee_packages` returns `[]` when `node.level > 0`, so relative imports are not tier-checked. A lower-tier module can use `from ..state import session_env` in `larch/core/` and pass `make py-lint` despite the same upward dependency as `from larch.state import session_env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Resolve relative imports to absolute larch.* from file path, or forbid/document relative cross-package imports.
  - From codex-specialist-correctness: Resolve relative imports against the importing module's package or reject any relative import that resolves to a higher-tier larch package, and add a regression test.
  - From cursor-specialist-edge-cases: Resolve relative imports against the importer file path to an absolute larch package and apply tier comparison; add relative-import tests
  - From codex-specialist-edge-cases: Resolve relative imports against the importer package before tiering them and check the resolved absolute target
  - From codex-specialist-testing: Resolve relative imports to their absolute `larch.*` target before tier comparison and update the tests to fail on upward relatives.
  - From codex-generalist: Resolve `ast.ImportFrom` nodes with `level > 0` against the importing module's package path, convert them to the corresponding `larch.*` package, then apply the same tier comparison. Add a regression test for `from ..state import ...` from `larch.core`.


