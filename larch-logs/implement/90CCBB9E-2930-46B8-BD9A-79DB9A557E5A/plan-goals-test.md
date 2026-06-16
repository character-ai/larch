## Goal
Implement issue #4500: [IMPLEMENTING] [OOS] test_agents CI-launcher harness targets leak vendor-failure diagnostics into the live /implement session's execution-issues.md.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Main agent

**Phase**: implement

**Vote tally**: N/A — auto-filed per policy


## Description

`python/test_agents.py` CI-launcher tests (e.g. `test_launch_cursor_ci`, `test_launch_codex_ci`, `test_check_reviewers`, `test_cursor_ci_stall_monitor`), when run via the `test-harnesses` Makefile targets under `skills/implement/scripts/run-step-checks.sh` (which exports `IMPLEMENT_TMPDIR`), append "Step ci fixer" vendor-failure diagnostics to `$IMPLEMENT_TMPDIR/execution-issues.md` — the LIVE /implement session's audit file — instead of a pytest-isolated tmpdir. Reproduction: observed during a real /implement run at Step 5 (pre-CI, coder=claude), where a full-coverage relevant-checks pass appended seven fabricated "ci fixer" CI-failure entries to the session `execution-issues.md` (codex binary-missing, claude backend-failed/malformed-JSON, cursor auth-preflight, cursor stall-monitor timeout whose body referenced a `pytest-of-<user>/pytest-NNNN/.../bin/cursor` fixture path), although no CI had run. Impact: those fabricated CI failures flow into the committed run log (`larch-logs/implement/<RUN_ID>/`) and the `larch:final-summary` report, corrupting per-run audit integrity on every /implement run whose relevant-checks reach `COVERAGE=full`. Likely cause (inferred, unverified): the vendor-failure-diagnostic append resolves its destination from the ambient `IMPLEMENT_TMPDIR` env var; the test fixtures isolate the vendor stub binary to a pytest tmpdir but not the diagnostic-append destination. Suggested fix options: (a) in the affected `test_agents.py` CI-launcher tests, monkeypatch `IMPLEMENT_TMPDIR` (and any execution-issues path resolver) to a `tmp_path` for the diagnostic-append code path; (b) make the diagnostic-append code take an explicit destination argument rather than falling back to ambient `IMPLEMENT_TMPDIR`; (c) have `run-step-checks.sh` run harness pytest with `IMPLEMENT_TMPDIR` unset or redirected so harness test runs can never write to the live session tmpdir.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
