## Goal
Implement issue #5118: [IMPLEMENTING] Keyword-only args: reports-runlogs-tokens [#5002 part 7/10].

## Implementation Plan
Part 7 of 10 of the #5002 keyword-only enforcement. Mechanizes a criterion-2 item from #4659; pairs with G-Py-3. Umbrella: #5002. **Blocked by part 0** (lint + baseline).

## Scope

In the **reports-runlogs-tokens** modules (19 files, ~11761 lines), add a leading `*` to every in-scope `def` / `async def` (2 or more non-`self`/`cls` params), then update all call sites to pass those arguments by name. Remove the converted defs from the part-0 baseline.

- `python/run_logs.py` (~3236 lines)
- `python/progress_report.py` (~2150 lines)
- `python/tokens.py` (~1715 lines)
- `python/timing.py` (~836 lines)
- `python/final_report.py` (~778 lines)
- `python/cleanup_implement_logs.py` (~586 lines)
- `python/report_tokens_cost.py` (~490 lines)
- `python/gc_run_logs.py` (~349 lines)
- `python/render_session_transcript.py` (~326 lines)
- `python/report_tokens_render.py` (~278 lines)
- `python/report_tokens_scan.py` (~254 lines)
- `python/gantt.py` (~135 lines)
- `python/report_tokens_models.py` (~133 lines)
- `python/report_tokens_cli.py` (~127 lines)
- `python/report_tokens_issue.py` (~111 lines)
- `python/report_tokens_plot.py` (~95 lines)
- `python/render_chart.py` (~76 lines)
- `python/run_log_tolerance.py` (~56 lines)
- `python/outcomes.py` (~30 lines)

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
