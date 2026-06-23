## Goal
Implement issue #5105: [IMPLEMENTING] Type local vars: ci [#5001 part 6/10].

## Implementation Plan
Part 6 of 10 of the #5001 local-variable typing audit. Enacts **G-Py-2** from #4659. Umbrella: #5001.

## Scope

Add type annotations to non-obvious local variables in the **ci** modules only (11 files, ~9113 lines):

- `python/stall_recovery.py` (~2669 lines)
- `python/checks.py` (~2503 lines)
- `python/ci_monitor.py` (~2071 lines)
- `python/ci_agentic_fix.py` (~820 lines)
- `python/ci.py` (~386 lines)
- `python/harness_ci_timing.py` (~212 lines)
- `python/pytest_ci_timing.py` (~176 lines)
- `python/pytest_sharding.py` (~99 lines)
- `python/harness_shard_packer.py` (~86 lines)
- `python/harness_makefile.py` (~54 lines)
- `python/ci_timing_fetch.py` (~37 lines)

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
