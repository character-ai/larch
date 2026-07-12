## Goal
Implement issue #7023: [IMPLEMENTING] contract-unification [FEATURE] Testkit foundation (paths, runners, process stubs).

## Implementation Plan
## Plan

## Approach

Extend the shared test foundation without migrating consumers.

- Add `ok(argv, stdout="")` for successful `CommandResult` values. Normalize `argv` to the tuple shape used by `CommandResult`. Set return code `0`, empty stderr, and the existing test duration convention.
- Add `completed(argv, stdout="")` for successful `subprocess.CompletedProcess[str]` values. Preserve the supplied argv and set return code `0` with empty stderr.
- Add `RecordingRunner.strict_queue(*responses)` as a class method that creates a strict runner with an ordered response list. Exhaustion must raise the existing `AssertionError`.
- Add `RecordingRunner.default_queue(default=None)` as a class method that creates a lenient runner. When `default` is absent, preserve the current per-call synthetic success result. When supplied, return that default after queue exhaustion.
- Add `repo_root()` as the single function form of the existing `ROOT` value. Keep `ROOT` and `CLI` available for current imports.
- Do not change existing consumers, wire fixtures, session helpers, or local result factories.

## Files to modify/create

### UPDATED: python/test_support.py

- Add the typed `ok()` and `completed()` factories near the shared result helpers.
- Add typed `RecordingRunner.strict_queue()` and `RecordingRunner.default_queue()` constructors.
- Build fresh response lists so callers cannot share mutable queue state.
- Add `repo_root()` returning the existing resolved `ROOT`.
- Preserve `RecordingRunner(...)`, `ROOT`, `CLI`, `run_cli()`, and all current behavior for existing callers.

### NEW: python/tests/support/

- Create the support-test package.
- Add `__init__.py` with a package docstring only.
- Add `test_foundation.py` as the focused unit-test module.
- Import the public helpers directly from `test_support`.

## Edge cases

- Accept any `Sequence[str]` supported by the runner and result types.
- Verify that `ok()` stores immutable command arguments in `CommandResult`.
- Verify empty and non-empty stdout.
- Verify that separate strict runners do not share response lists or indexes.
- Verify strict exhaustion raises after all queued responses are consumed.
- Verify a lenient runner without an explicit default creates a success result for the actual call argv.
- Verify a lenient runner with an explicit default returns that result on exhaustion.
- Verify `repo_root() == ROOT` and `CLI == repo_root() / "python" / "cli.py"`.

## Failure modes

- Avoid changing the existing default `RecordingRunner()` semantics.
- Avoid passing a tuple directly into the mutable `responses` field.
- Keep `CompletedProcess` arguments and generic string output types consistent with current tests and type checking.
- Keep tests below `python/tests/` so `lint_flat_tests` retains `python/test_support.py` as the only root exemption.
- Do not introduce duplicate helper blocks that trigger the R0801 ratchet.

## Testing strategy

- Run `python3 -m pytest python/tests/support/test_foundation.py -q` while iterating.
- Run `python3 python/cli.py lint flat-tests`.
- Run `make py-test`.
- Run `make py-lint-checks-fast`.
- Run the repository duplicate-code lint target to confirm no R0801 regression.
- Confirm the working diff contains only `python/test_support.py` and `python/tests/support/`.

## Acceptance

- Run `python3 -m pytest python/tests/support/test_foundation.py -q` while iterating.
- Run `python3 python/cli.py lint flat-tests`.
- Run `make py-test`.
- Run `make py-lint-checks-fast`.
- Run the repository duplicate-code lint target to confirm no R0801 regression.
- Confirm the working diff contains only `python/test_support.py` and `python/tests/support/`.

diff_added: 105
diff_deleted: 0
mechanical_churn: false
diff_lines: 105

## Test plan
(no test plan section in plan-file)
