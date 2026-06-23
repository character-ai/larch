## Goal
Implement issue #5106: [IMPLEMENTING] Type local vars: reports-runlogs-tokens [#5001 part 7/10].

## Implementation Plan
Part 7 of 10 of the #5001 local-variable typing audit. Enacts **G-Py-2** from #4659. Umbrella: #5001.

## Scope

Add type annotations to non-obvious local variables in the **reports-runlogs-tokens** modules only (19 files, ~11761 lines):

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
