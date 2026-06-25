## Goal
Implement issue #5120: [IMPLEMENTING] Keyword-only args: session-bootstrap-cli [#5002 part 9/10].

## Implementation Plan
Part 9 of 10 of the #5002 keyword-only enforcement. Mechanizes a criterion-2 item from #4659; pairs with G-Py-3. Umbrella: #5002. **Blocked by part 0** (lint + baseline).

## Scope

In the **session-bootstrap-cli** modules (24 files, ~11084 lines), add a leading `*` to every in-scope `def` / `async def` (2 or more non-`self`/`cls` params), then update all call sites to pass those arguments by name. Remove the converted defs from the part-0 baseline.

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
