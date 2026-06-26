### FINDING_1: Private timing helper must use Runner, not subprocess-only recording
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: blocking
- **Concern**: The planned private timing helper does not take or route through the existing `Runner` passed into `run_relevant_checks` / `run_lint_fix`, unlike `_mark_step_ledger`. The helper spec only describes invoking `python/cli.py timing record-vendor-task` via env vars (or shelling out directly, as `_record_coder_vendor_task` does in `review_and_fix.py`). Planned `test_checks.py` assertions require `StubRunner.calls` on `timing record-vendor-task`. A subprocess-only helper would pass runtime but fail mandated tests, diverge from the established `checks.py` pattern, and force extra monkeypatching to observe recording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add runner: Runner to the helper signature and invoke record-vendor-task through runner.run with the same IMPLEMENT_TMPDIR / LARCH_TIMING_SKILL / DESIGN_TMPDIR env contract as _mark_step_ledger.
  - From Cursor-Innovation: Define the helper as `_record_checks_vendor_task(*, runner: Runner, ...)` and invoke `runner.run([...])` with the same env pattern as `_mark_step_ledger`; call it from both public wrappers with the existing `runner` argument

### FINDING_2: run_lint_fix wrapper spec omits full try/finally timing envelope
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The `run_lint_fix` refactor bullets still omit explicit `outcome = None`, `start_s` capture, and `return outcome` even though `run_relevant_checks` lists them and Failure modes require the full envelope. `run_relevant_checks` bullets require both initializations; `run_lint_fix` bullets jump straight to try/finally without them. A literal implementer following only the lint-fix subsection can hit `UnboundLocalError` in `finally` on exceptions, emit rows with missing/wrong `start_s`, leave exception paths unlabeled, or return inside `try` without proper `--start-s`/`--end-s` on success—recreating the silent-gap bug class on lint-fix exception paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the same two bullets to the run_lint_fix wrapper spec as run_relevant_checks: initialize outcome = None and capture start_s = int(time.time()) before the try block.
  - From Cursor-Innovation: Copy the explicit `run_relevant_checks` bullets into the `run_lint_fix` section: initialize `outcome = None`, capture `start_s` before `try`, assign `outcome = _run_lint_fix_impl(...)` inside `try` only, compute `end_s = int(time.time())` in `finally`, then `return outcome` after the block

### FINDING_3: test_timing.py plan bullet incomplete for new task kinds
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The `test_timing.py` update is an incomplete sentence and does not name the new task kinds. The plan says to extend accepted-kind tests and assert no unknown task-kind warning, but the parameterized kinds line is blank. Without `claude-relevant-checks` and `claude-lint-fix` in `test_timing.py`, allow-list drift can ship and every new wrapper call will emit stderr warning noise despite `timing.py` being updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Complete the bullet: parametrize claude-relevant-checks and claude-lint-fix in a test_timing_record_vendor_task_accepts_* test mirroring the existing review-fix parametrized pattern, and assert unknown task-kind is absent.
```

**Merge summary**

| Merged ID | Source inputs | Rationale |
|-----------|---------------|-----------|
| `FINDING_1` | Cursor-Arch #1 + Cursor-Innovation #5 | Same fix: timing helper must use `Runner.run`, not subprocess-only recording |
| `FINDING_2` | Cursor-Arch #2 + Cursor-Innovation #4 | Same fix: `run_lint_fix` needs the full timing envelope mirrored from `run_relevant_checks` |
| `FINDING_3` | Cursor-Arch #3 only | Distinct surface: `test_timing.py` allow-list coverage, separate from helper/wrapper specs |
