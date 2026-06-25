## Goal
Implement issue #5117: [IMPLEMENTING] Keyword-only args: ci [#5002 part 6/10].

## Implementation Plan
Part 6 of 10 of the #5002 keyword-only enforcement. Mechanizes a criterion-2 item from #4659; pairs with G-Py-3. Umbrella: #5002. **Blocked by part 0** (lint + baseline).

## Scope

In the **ci** modules (11 files, ~9113 lines), add a leading `*` to every in-scope `def` / `async def` (2 or more non-`self`/`cls` params), then update all call sites to pass those arguments by name. Remove the converted defs from the part-0 baseline.

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
