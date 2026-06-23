## Goal
Implement issue #5109: [IMPLEMENTING] Type local vars: research-implement-lints [#5001 part 10/10].

## Implementation Plan
Part 10 of 10 of the #5001 local-variable typing audit. Enacts **G-Py-2** from #4659. Umbrella: #5001.

## Scope

Add type annotations to non-obvious local variables in the **research-implement-lints** modules only (24 files, ~10524 lines):

- `python/analyze_issues.py` (~1785 lines)
- `python/research_eval.py` (~957 lines)
- `python/audit_runs.py` (~948 lines)
- `python/research.py` (~805 lines)
- `python/duplicate_code.py` (~551 lines)
- `python/retro_v3_sweep.py` (~117 lines)
- `python/implement_dispatch.py` (~1722 lines)
- `python/execution_issues.py` (~326 lines)
- `python/dirty_tree.py` (~283 lines)
- `python/phantom.py` (~202 lines)
- `python/coder_delta_guards.py` (~125 lines)
- `python/lint_complexity_baseline.py` (~495 lines)
- `python/lint_mermaid_fences.py` (~298 lines)
- `python/lint_consecutive_bash.py` (~270 lines)
- `python/check_topology_rule_paths.py` (~256 lines)
- `python/lint_codex_exec_auth.py` (~227 lines)
- `python/lint_skill_invocations.py` (~219 lines)
- `python/lint_no_raw_stderr_after_quiet_init.py` (~174 lines)
- `python/lint_skill_md_flag_signature.py` (~173 lines)
- `python/lint_readability_preamble.py` (~157 lines)
- `python/lint_literal_counts.py` (~131 lines)
- `python/lint_common.py` (~114 lines)
- `python/lint_gh_body_inline.py` (~112 lines)
- `python/lint_run_log_run_id.py` (~77 lines)

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
