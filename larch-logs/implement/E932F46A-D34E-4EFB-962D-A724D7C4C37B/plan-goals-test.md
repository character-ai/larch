## Goal
Implement issue #5655: [IMPLEMENTING] [py-code-quality] Packaging follow-up: move 8 residual flat runtime modules into larch.* and delete dead design_legacy.py.

## Implementation Plan
**Follow-up to umbrella #4982.** The 9/9 capstone (#5175, PR #5653) moved ~60 runtime modules into `larch.*`, but its "sweep up any remaining flat modules" step missed 8 runtime modules. They still sit flat in `python/` and are imported by package code via flat top-level names, resolving only because pytest's `pythonpath=["."]` keeps flat modules importable. That is the exact crutch the umbrella set out to remove ("No package boundaries enforce layering").

**Scope.** Move these 8 modules into the package matching their dominant consumer, repoint every importer (runtime and tests) to the `larch.*` path, and add no new shims. `/design` finalizes each home to minimize new cross-package edges.

| Flat module | LOC | Suggested home | `larch.*` import sites |
|---|---|---|---|
| `ctx` (defines `Ctx`) | 106 | `larch.core` | agents/agents.py, design/design_lifecycle.py, design/plan_quality.py |
| `env_file` | 46 | `larch.core` | core/cleanup_skill.py, report/progress_report.py |
| `coder_delta_guards` | 125 | `larch.implement` (or `larch.core` to avoid a `larch.git` to `larch.implement` edge) | git/rebase.py, implement/checks.py, implement/ci_agentic_fix.py |
| `design_diagram_log` | 150 | `larch.report` or `larch.design` | design/design_publish.py, git/pr_body.py, report/run_logs.py |
| `exec_issue_detail` | 440 | `larch.report` or `larch.issue` | design/design_summary.py, report/final_report.py |
| `review_phase_detail` | 94 | `larch.report` or `larch.review` | design/design_summary.py, report/final_report.py |
| `run_log_tolerance` | 56 | `larch.report` | issue/audit_runs.py, report/run_logs.py |
| `self_review_tally` | 48 | `larch.review` or `larch.report` | issue/audit_runs.py |

Total: 18 runtime import sites plus each module's test imports.

**Also delete `python/design_legacy.py`** (39 LOC). It is imported by nobody. The only references are a path-string fixture in `test_checks.py` and a "design_legacy round" timing-row label string in `test_progress_report.py`, neither of which imports the module. Remove the module and update that fixture.

**Out of scope (intentional residual).** Four flat modules are test/CI-harness support imported only by tests, never by `larch.*` runtime: `ci_timing_fetch`, `pytest_ci_timing`, `pytest_sharding`, `review_test_support`. They are conftest-like and stay flat alongside the flat test files. The 45 backward-compat `sys.modules` shims are handled by the sibling follow-up.

**Acceptance.**
- The 8 modules live under `larch.*` packages.
- No file under `python/larch/` imports a flat top-level module (no `from ctx import ...`, no `import coder_delta_guards`).
- `design_legacy.py` deleted.
- `make py-lint` and `make py-test` green.
- No new shims added. No behavior change; pure restructuring plus import rewrites.

**Effort / risk.** Medium / low.

## Test plan
(no test plan section in plan-file)
