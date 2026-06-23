## Goal
Implement issue #5108: [IMPLEMENTING] Type local vars: session-bootstrap-cli [#5001 part 9/10].

## Implementation Plan
Part 9 of 10 of the #5001 local-variable typing audit. Enacts **G-Py-2** from #4659. Umbrella: #5001.

## Scope

Add type annotations to non-obvious local variables in the **session-bootstrap-cli** modules only (24 files, ~11084 lines):

- `python/rendering.py` (~1963 lines)
- `python/bootstrap.py` (~1776 lines)
- `python/session_env.py` (~1721 lines)
- `python/cli.py` (~756 lines)
- `python/redact.py` (~613 lines)
- `python/architectural_guidelines.py` (~569 lines)
- `python/forked_repo.py` (~550 lines)
- `python/upgrade_larch.py` (~502 lines)
- `python/config.py` (~400 lines)
- `python/larch_io.py` (~356 lines)
- `python/migration_lint.py` (~350 lines)
- `python/logging_util.py` (~220 lines)
- `python/proc.py` (~215 lines)
- `python/run_context.py` (~186 lines)
- `python/cleanup_skill.py` (~174 lines)
- `python/verify_skill.py` (~144 lines)
- `python/residual_bash.py` (~117 lines)
- `python/ctx.py` (~106 lines)
- `python/retry.py` (~103 lines)
- `python/alias_skill.py` (~97 lines)
- `python/env_file.py` (~46 lines)
- `python/errors.py` (~45 lines)
- `python/verify_main.py` (~44 lines)
- `python/repo_roots.py` (~31 lines)

## What to annotate

Locals whose type is not obvious from the right-hand side. Keep diffs surgical. Touch only the files listed above.

## Carve-outs (leave un-annotated, obvious RHS)

`count = 0`, loop targets, `x = Foo()`, a value returned by an already-typed call. Annotating these adds noise.

## Not lint-enforceable

ruff `ANN` covers signatures, not locals (see #5003). This is a manual audit pass for this domain.

## Excluded (do not touch, stated in every chunk and the umbrella)

- All test files: `python/test_*.py` and `python/conftest.py`.
- Everything under `larch-logs/`.
- Every `.py` outside `python/` (skill scripts, repo-root helpers).

Audit surface is `python/` non-test source only.

## Acceptance

- Non-obvious locals in the listed files carry annotations.
- `pyright` clean; `make py-test` green.
- No source changes outside the listed files.

## Test plan
(no test plan section in plan-file)
