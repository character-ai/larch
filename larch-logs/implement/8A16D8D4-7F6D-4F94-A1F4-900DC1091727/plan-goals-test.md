## Goal
Implement issue #5116: [IMPLEMENTING] Keyword-only args: ship-pr-release [#5002 part 5/10].

## Implementation Plan
Part 5 of 10 of the #5002 keyword-only enforcement. Mechanizes a criterion-2 item from #4659; pairs with G-Py-3. Umbrella: #5002. **Blocked by part 0** (lint + baseline).

## Scope

In the **ship-pr-release** modules (13 files, ~8729 lines), add a leading `*` to every in-scope `def` / `async def` (2 or more non-`self`/`cls` params), then update all call sites to pass those arguments by name. Remove the converted defs from the part-0 baseline.

- `python/ship.py` (~2521 lines)
- `python/finalize.py` (~1190 lines)
- `python/pr_body.py` (~840 lines)
- `python/version_bump.py` (~654 lines)
- `python/rebase.py` (~632 lines)
- `python/merge.py` (~618 lines)
- `python/pr.py` (~488 lines)
- `python/push.py` (~439 lines)
- `python/closeout.py` (~400 lines)
- `python/step_7a.py` (~354 lines)
- `python/release_finish.py` (~231 lines)
- `python/release_prepare.py` (~230 lines)
- `python/promote_release.py` (~132 lines)

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
