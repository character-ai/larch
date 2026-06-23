## Goal
Implement issue #5100: [IMPLEMENTING] Type local vars: design-lifecycle [#5001 part 1/10].

## Implementation Plan
Part 1 of 10 of the #5001 local-variable typing audit. Enacts **G-Py-2** from #4659. Umbrella: #5001.

## Scope

Add type annotations to non-obvious local variables in the **design-lifecycle** modules only (17 files, ~11652 lines):

- `python/design_lifecycle.py` (~4332 lines)
- `python/clarify.py` (~1193 lines)
- `python/decompose.py` (~741 lines)
- `python/plan_scout.py` (~722 lines)
- `python/issue_wire.py` (~630 lines)
- `python/design_publish.py` (~507 lines)
- `python/design_log_publish_flow.py` (~473 lines)
- `python/design_pause.py` (~452 lines)
- `python/design_oos.py` (~425 lines)
- `python/design_summary.py` (~420 lines)
- `python/preflight.py` (~414 lines)
- `python/design_log_ship.py` (~330 lines)
- `python/design_argv.py` (~309 lines)
- `python/design_postplan.py` (~272 lines)
- `python/design_step_log.py` (~243 lines)
- `python/design_diagram_log.py` (~150 lines)
- `python/design_legacy.py` (~39 lines)

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
