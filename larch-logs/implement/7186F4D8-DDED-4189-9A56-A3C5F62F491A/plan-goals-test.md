## Goal
Implement issue #5112: [IMPLEMENTING] Keyword-only args: design-lifecycle [#5002 part 1/10].

## Implementation Plan
Part 1 of 10 of the #5002 keyword-only enforcement. Mechanizes a criterion-2 item from #4659; pairs with G-Py-3. Umbrella: #5002. **Blocked by part 0** (lint + baseline).

## Scope

In the **design-lifecycle** modules (17 files, ~11652 lines), add a leading `*` to every in-scope `def` / `async def` (2 or more non-`self`/`cls` params), then update all call sites to pass those arguments by name. Remove the converted defs from the part-0 baseline.

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

Note: the `def` edits are confined to the files above, but call-site updates may touch other `python/` source files. That is expected and safe under the single-runner invariant.

## Test files: fix only what breaks

Test files are not an audit target. No test-defined function gets `*`; no test local is touched. Sole exception: when adding `*` to one of the source functions above breaks an existing positional call in a test, switch that one call to keyword form, solely to keep `make py-test` green. This matches the #5002 umbrella decision.

## Carve-outs (do not add `*`)

- Single-parameter functions.
- Dunders and operator/protocol methods with fixed signatures.
- Signatures dictated by an external API or callback contract.

## Excluded (do not touch, stated in every chunk and the umbrella)

- All test files: `python/test_*.py` and `python/conftest.py`.
- Everything under `larch-logs/`.
- Every `.py` outside `python/` (skill scripts, repo-root helpers).

Audit surface is `python/` non-test source only.

## Acceptance

- In-scope defs in the listed files are keyword-only; all call sites updated, including the minimal test call-site fixes above.
- Converted defs removed from the part-0 baseline.
- `make py-lint` and `make py-test` green.

## Test plan
(no test plan section in plan-file)
