## Goal
Implement issue #5656: [IMPLEMENTING] [py-code-quality] Packaging follow-up: remove the 45 backward-compat sys.modules shims and repoint flat test imports to larch.*.

## Implementation Plan
**Follow-up to umbrella #4982.** The 9/9 capstone (#5175, PR #5653) left 45 flat `python/*.py` files as backward-compat `sys.modules` shims: 4-line redirects of the form `import larch.<pkg>.<mod> as _m; sys.modules[__name__] = _m`. They exist so flat imports (`import rendering`, `import research`, ...) keep resolving after the real code moved into `larch.*`. The repo ethos is "No shims" and "repoint consumers"; this issue finishes that.

**Scope.**
- Repoint every remaining flat local import that resolves through a shim (`import <name>` / `from <name> import ...`, mostly in the test suite, ~17 sites today) to its canonical `larch.*` path.
- Delete the 45 shim files once no flat importer remains.
- `python/cli.py` stays. It is the one sanctioned entry-point shim backing the consumer contract `python3 python/cli.py <domain> <verb>`, not a back-compat module shim. Out of scope.

**Acceptance.**
- No backward-compat `sys.modules` shim files remain under `python/` (only the `cli.py` entry-point shim stays).
- No flat local-module import remains anywhere, runtime or tests; every intra-repo import is `larch.*`-qualified.
- `make py-lint` and `make py-test` green. No behavior change.

**Sequencing.** Blocked by the module-move follow-up. Do the 8-module move first, then this teardown sweeps the final, stable set so the "zero flat runtime imports, zero shims" invariant lands in one PR. Sequencing also keeps two `/implement` runs from churning the same test files (single-runner invariant).

**Effort / risk.** Medium / low-medium. Wide but mechanical test-import surface.

## Test plan
(no test plan section in plan-file)
