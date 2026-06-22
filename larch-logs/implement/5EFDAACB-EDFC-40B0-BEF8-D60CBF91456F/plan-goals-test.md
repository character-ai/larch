## Goal
Implement issue #5103: [IMPLEMENTING] Type local vars: voting-agents [#5001 part 4/10].

## Implementation Plan
Part 4 of 10 of the #5001 local-variable typing audit. Enacts **G-Py-2** from #4659. Umbrella: #5001.

## Scope

Add type annotations to non-obvious local variables in the **voting-agents** modules only (6 files, ~11064 lines):

- `python/agents.py` (~6145 lines)
- `python/voting.py` (~1917 lines)
- `python/collect_results.py` (~1131 lines)
- `python/agent_waterfall.py` (~981 lines)
- `python/agent_voters.py` (~549 lines)
- `python/admission.py` (~341 lines)

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
