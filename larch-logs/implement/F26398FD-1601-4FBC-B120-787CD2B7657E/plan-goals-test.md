## Goal
Implement issue #5167: [IMPLEMENTING] [py-code-quality] Packaging 1/9: foundation larch/ package with larch.io, larch.errors, core leaf utils.

## Implementation Plan
**Problem.** All runtime modules sit flat in `python/` and import each other by top-level name (`import proc`, `from config import ...`). There is no package to anchor the move, and the most-depended-on leaf utilities are imported nearly everywhere: `proc` (57 importers), `logging_util` (49), `redact` (42), `config` (39), `larch_io` (34), `errors` (22). Nothing can move into a package until the package exists and the shared leaf layer lands first.

**Proposed change.** Create the `python/larch/` package (`__init__.py`) and move the shared leaf layer into it: `larch.io` (from `larch_io`), `larch.errors` (from `errors`/`outcomes`), and a core utils home for `proc`, `config`, `logging_util`, `redact`, `retry`, `run_context`. Rewrite every importer to `from larch... import ...`. Update `python/pyproject.toml` `pythonpath`, `conftest.py` test discovery, `test_stdlib_only.py`, and `ruff.toml` / `ruff-complexity-audit.toml` so lint and tests find the package. This child establishes the convention every later child follows. Exact module-to-subpackage boundary is finalized in this child's `/design`.

**Out of scope / don't-touch.** No behavior change. Keep the `python3 cli.py <domain> <verb>` invocation contract and all wire formats. Pure restructuring plus import rewrites. Do not move domain modules (later children).

**Acceptance.** `python/larch/` exists with the shared leaf layer; all importers repointed; `make py-lint` / `make py-test` green; consumer invocations (`python3 python/cli.py ...`) unchanged.

**Effort / risk.** Medium / medium. Widest import blast radius, but purely mechanical. Land first.

**Dependencies.** Root of the packaging sub-tree. Original blockers (#4975 larch_io, #4979 god-function split) are already DONE. Blocks every other packaging child. Tracked under umbrella #4982. Wired via `/block-issue`.

## Test plan
(no test plan section in plan-file)
