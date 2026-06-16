## Goal
Implement issue #4495: [IMPLEMENTING] [BUG] py-test CI-fixer tests pollute a live session's execution-issues.md….

## Implementation Plan
## Summary

CI-fixer tests in `python/test_agents.py` write into a **live larch session's** `execution-issues.md` and `vendor-failure-diagnostics.parts/` when `make py-test` runs **inside** an `/implement` or `/design` session. The CI-fixer production code resolves its output target from ambient environment variables (`IMPLEMENT_TMPDIR`, `SESSION_ENV_PATH`, etc.) that larch exports, and `python/conftest.py`'s autouse isolation does not scrub those vars, so the tests' simulated failures land in the real session tmpdir and get flushed into the committed run log and the tracking issue's execution-issues summary. This is a test-isolation defect (hygiene), not a security issue; the carrying run's code diff is unaffected.

## Original report

Discovered during an `/implement --emergency --self-review` run. A freshly-created session tmpdir (`~/.cache/larch/sessions/claude-implement-<repo>-<id>/execution-issues.md`) accumulated a `### CI Issues` section full of simulated CI-fixer failures (codex "binary missing"; claude "backend failed" / "Malformed Claude CI JSON" / empty `{"result":""}`; cursor auth-preflight failure; cursor `LARCH_CURSOR_MODEL must not contain POSIX [[:cntrl:]] characters`; cursor stall/timeout), even though the run never reached CI and Step 0 reported both Codex and Cursor available. The identical block appeared exactly twice (once per `make py-test`: Step 3 checks + Step 5 self-review checks), and `vendor-failure-diagnostics.parts/` held 14 part files (~7 fixtures x 2 runs). The git clone working tree stayed clean throughout; the polluted file lives in the per-session cache outside the repo.

## Reproduction scenario

1. Start an `/implement` (or `/design`) run so `IMPLEMENT_TMPDIR` and `SESSION_ENV_PATH` are exported into the environment.
2. During Step 3 / Step 5 relevant-checks, `make py-test` runs as a child process and inherits those env vars.
3. Inspect `$IMPLEMENT_TMPDIR/execution-issues.md` and `$IMPLEMENT_TMPDIR/vendor-failure-diagnostics.parts/`: both gain test-fixture CI failures that no real CI produced.

Minimal standalone repro (no full run needed):

```bash
export IMPLEMENT_TMPDIR="$(mktemp -d)"
make py-test
ls "$IMPLEMENT_TMPDIR/execution-issues.md" "$IMPLEMENT_TMPDIR/vendor-failure-diagnostics.parts" 2>&1
# BUG: these exist after the suite runs; they should not.
```

## Expected behavior

`make py-test` is hermetic. CI-fixer tests must not write into whatever session tmpdir happens to be referenced by ambient env vars. All test artifacts stay under pytest `tmp_path`.

## Observed behavior

Running the suite inside a live session appends ~7 simulated CI-fixer failures per run to the live session's `execution-issues.md` (observed twice: Step 3 + Step 5) and creates 14 `vendor-failure-diagnostics.parts/part.*` files. These get flushed into the committed run log (`larch-logs/implement/<run-id>/execution-issues.ndjson`, `vendor-failure-diagnostics.txt`) and into the tracking issue's execution-issues summary, falsely implying real CI tooling failures.

## Root cause analysis

`python/agents.py` resolves its output target from ambient environment variables:

- `_resolve_execution_issues_log()` (`python/agents.py:2020`) keys off `LARCH_EXECUTION_ISSUES_LOG`, then `SESSION_ENV_PATH`, then `IMPLEMENT_TMPDIR` / `DESIGN_TMPDIR` / `REVIEW_TMPDIR`.
- `_append_vendor_failure_diagnostics()` (`python/agents.py:2031`) keys off `IMPLEMENT_TMPDIR`.

CI-fixer tests exercise the real `_append_ci_failure` (`python/agents.py:2052`) path, which calls both resolvers. The tests do not scrub those env vars. `python/conftest.py`'s autouse `_quiet_test_isolation` (lines 14-26) only sets `LARCH_QUIET_DISABLE`; it never `delenv`s the session-routing vars. Outside a live session the vars are unset, so `_resolve_execution_issues_log` returns `None` and `_append_vendor_failure_diagnostics` returns early, which is why standalone CI never sees it. Inside a live larch session the vars point at the real tmpdir, so the leak fires. The conftest docstring (lines 18-19) already acknowledges that tests inherit env "inside `python/cli.py checks run-relevant`" from the parent script: the same inheritance path, just never extended to the session-tmpdir vars.

## Evidence

- `python/agents.py:2020-2028` - `_resolve_execution_issues_log` env precedence (`LARCH_EXECUTION_ISSUES_LOG` -> `SESSION_ENV_PATH` -> `IMPLEMENT_TMPDIR`/`DESIGN_TMPDIR`/`REVIEW_TMPDIR`).
- `python/agents.py:2031-2035` - `_append_vendor_failure_diagnostics` reads `os.environ.get("IMPLEMENT_TMPDIR")` and writes `vendor-failure-diagnostics.parts/`.
- `python/agents.py:2052-2090` - `_append_ci_failure` emits a `run-log append-failure --category "CI Issues"` entry and calls the vendor-diagnostics writer.
- `python/conftest.py:14-26` - autouse isolation scrubs only `LARCH_QUIET_DISABLE`; docstring (18-19) notes env inheritance from `checks run-relevant`.
- Live-run observation: two identical `### CI Issues` blocks (one per py-test run) plus 14 `vendor-failure-diagnostics.parts/part.*` files in the session tmpdir; `git status --short` on the clone stayed empty (artifacts are in `~/.cache/larch/sessions/<unique-tmpdir>/`, not the repo).
- Cursor fixture string `must not contain POSIX [[:cntrl:]] characters` matches production raises at `python/agents.py:421` / `:470`, confirming the entries originate from exercising agents.py code paths.

## Affected files

- `python/conftest.py` - autouse isolation is missing the session-routing env vars (primary fix locus).
- `python/test_agents.py` - the CI-fixer tests that trigger the leak; natural home for a regression test.
- `python/agents.py` - `_resolve_execution_issues_log` / `_append_vendor_failure_diagnostics` / `_append_ci_failure`: env-keyed resolvers are correct for production but are the source of the test-time leak.

## Suggested fix(es)

- **Primary:** extend `python/conftest.py`'s autouse isolation to `monkeypatch.delenv(name, raising=False)` for `IMPLEMENT_TMPDIR`, `DESIGN_TMPDIR`, `REVIEW_TMPDIR`, `SESSION_ENV_PATH`, and `LARCH_EXECUTION_ISSUES_LOG`, mirroring the existing `_quiet_test_isolation` pattern. Tests that need these set their own via `monkeypatch.setenv`.
- **Regression test:** with `IMPLEMENT_TMPDIR` set in the environment, invoke the CI-fixer append path and assert it does not create files under that directory.
- **Verification:** `IMPLEMENT_TMPDIR=$(mktemp -d) make py-test`, then assert `$IMPLEMENT_TMPDIR/execution-issues.md` and `$IMPLEMENT_TMPDIR/vendor-failure-diagnostics.parts` are not created.
- This is the same class as #3593 / PR #3607 ("Fix LARCH_QUIET_* env leak into checks pipeline harnesses"), which fixed quiet-env leakage via the same autouse-conftest mechanism. The env-keyed execution-issues / vendor-failure resolvers landed/changed later (#3673, #3684, #4167) without extending that isolation.

## Open questions

- Should the conftest scrub be global (all session-routing vars) or scoped to the agents/CI-fixer test module? Global matches the #3593 precedent and is safer.
- Are there other resolvers (token ledger, timing ledger, run-log roots) that read these env vars and could similarly leak during in-session test runs? A short audit is warranted.

## Test plan
(no test plan section in plan-file)
