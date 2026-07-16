## Goal
Implement issue #7488: [IMPLEMENTING] contract-unification [DEDUP] Migrate the remaining exact queue-runner test doubles.

## Implementation Plan
#### Problem

An exact clone scan found the same subprocess queue-runner protocol in 14 Python test files and 23 occurrences. `python/test_support.py` already provides shared runner support from the earlier Big-5 migration, but many report, git, implement, issue, and release tests still reproduce argv recording, queued results, callbacks, fd routing, and exhaustion behavior.

#### Goal

Extend the shared test support with declarative argv matchers, queued results, callbacks, and stdout/stderr fd routing. Migrate only exact protocol clones in a bounded first batch. Retain domain-specific subclasses whose behavior is not shared. Preserve assertion quality by keeping expected argv at each test site.

#### Exact scope

The scan identified the common `Runner.run(Sequence[str], timeout, cwd, env, check, stdout, stderr)` protocol in exactly these 14 files for this batch: `release/test_version_bump.py`, `state/test_session_env.py`, `issue/test_learn_from_bugs.py`, `issue/test_analyze_bugs_runtime.py`, `review/test_review_pipeline.py`, `implement/test_ci_monitor.py`, `implement/test_checks.py`, `report/test_run_logs.py`, `report/test_report_tokens_plot.py`, `report/test_report_tokens_issue.py`, `report/test_report_tokens_scan.py`, `report/test_report_tokens_cost.py`, `git/test_git.py`, and `git/test_gh.py`.

#### Required implementation

- Extend the existing `python/test_support.py::RecordingRunner`; do not add another shared test-support package or production abstraction.
- Support ordered queued `CommandResult` values, a strict exhaustion mode, a default result, expected argv or predicate matchers, callbacks that can inspect call options, and explicit stdout/stderr fd routing needed by current tests.
- Provide precise mismatch messages containing call index, expected matcher, actual argv, and remaining queue length.
- Keep call recording immutable from the test's perspective. Preserve `timeout`, `cwd`, `env`, `check`, `stdout`, and `stderr` for assertions instead of discarding them when a migrated test needs those values.
- Migrate only local runners whose behavior is expressible without condition-heavy shared code. Keep domain-specific state machines and failure injectors local.
- Preserve expected argv near each test. Do not replace explicit command assertions with broad snapshots or substring matching.

#### Verification

Add focused shared-runner tests for ordered success, strict exhaustion, default fallback, matcher failure, callback exception, fd routing, and option capture. Run all 14 test modules. Search those modules for the copied full protocol signature and document any retained occurrence with a concrete domain-specific reason.

#### Size and acceptance

Expected change: 900-1,400 lines with a net reduction. Shared tests must pin exhaustion and mismatch diagnostics. The selected 14 files must no longer contain the copied protocol, and unrelated specialized runners remain untouched.

## Test plan
(no test plan section in plan-file)
