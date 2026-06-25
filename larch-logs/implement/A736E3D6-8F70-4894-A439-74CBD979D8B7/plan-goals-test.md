## Goal
Implement issue #5119: [IMPLEMENTING] Keyword-only args: github-issues-infra [#5002 part 8/10].

## Implementation Plan
Part 8 of 10 of the #5002 keyword-only enforcement. Mechanizes a criterion-2 item from #4659; pairs with G-Py-3. Umbrella: #5002. **Blocked by part 0** (lint + baseline).

## Scope

In the **github-issues-infra** modules (13 files, ~10384 lines), add a leading `*` to every in-scope `def` / `async def` (2 or more non-`self`/`cls` params), then update all call sites to pass those arguments by name. Remove the converted defs from the part-0 baseline.

- `python/gh.py` (~1751 lines)
- `python/git.py` (~1678 lines)
- `python/combine_issues.py` (~1203 lines)
- `python/file_oos.py` (~1110 lines)
- `python/tracking_issue.py` (~1028 lines)
- `python/issue_create.py` (~969 lines)
- `python/deps_audit.py` (~926 lines)
- `python/oos_filer.py` (~832 lines)
- `python/issue_query.py` (~238 lines)
- `python/oos.py` (~214 lines)
- `python/blocker.py` (~177 lines)
- `python/oos_disposition.py` (~136 lines)
- `python/issue_block.py` (~122 lines)

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
