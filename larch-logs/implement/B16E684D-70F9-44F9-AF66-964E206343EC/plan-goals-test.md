## Goal
Implement issue #5121: [IMPLEMENTING] Keyword-only args: research-implement-lints [#5002 part 10/10].

## Implementation Plan
Part 10 of 10 of the #5002 keyword-only enforcement. Mechanizes a criterion-2 item from #4659; pairs with G-Py-3. Umbrella: #5002. **Blocked by part 0** (lint + baseline).

## Scope

In the **research-implement-lints** modules (24 files, ~10524 lines), add a leading `*` to every in-scope `def` / `async def` (2 or more non-`self`/`cls` params), then update all call sites to pass those arguments by name. Remove the converted defs from the part-0 baseline.

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
