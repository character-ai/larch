## Goal
Implement issue #5891: [IMPLEMENTING] [Bug] /implement terminal: checks-commit-route child killed by SIGTERM (timeout) while test suite exceeded wrapper's time limit; standalone checks confirm RELEVANT_CHECKS_OK=true (unrecoverable at 3).

## Implementation Plan
<!-- larch-stall:signature=911d19de565e5156b0fa331645c148cf0b8f9d30a90465455da2adbba1d9ca3f -->
## Report metadata
- **Report kind**: `terminal-failure`
- **Failure class**: `unrecoverable`
- **Step**: `3`
- **Bail reason**: `redacted`
- **Run ID**: `76C8CACA-C9BC-4544-9224-0EC8A3DEBEAF`
- **Branch**: `unknown`
- **PR URL**: `unknown`

## Root-cause finding

verdict=environment
confidence=high
summary=checks-commit-route child killed by SIGTERM (timeout) while test suite exceeded wrapper's time limit; standalone checks confirm RELEVANT_CHECKS_OK=true

The `checks-commit-route --checks-site step3` wrapper ran `python/cli.py checks
run-relevant --site step3` but the child was killed by SIGTERM (EXIT_CODE=-15)
before completing.

Evidence:
- `stall-recovery-classification.env`: MATCHED_CLASSIFIER_PATTERN=no-stall,
  FAILURE_CLASS=unrecoverable (no matching stall pattern)
- Standalone `python/cli.py checks run-relevant --site step3`: RELEVANT_CHECKS_OK=true
  SITE=step3 COVERAGE=full (run successfully after the stall, same turn)
- Full test suite run: 4055 passed, 48 skipped, 1 pre-existing fixture-missing
  failure (unrelated to this PR) — duration ~450 seconds
- Complexity baseline lint: 0 violations after `make regen-complexity-baseline`
- `ruff check` on all new and modified files: 0 errors

The test suite takes ~450 seconds; the checks wrapper has a shorter timeout.
The code changes are correct and all checks pass when run without time pressure.
This is an environment constraint, not a code defect.



## Attempts

| Attempt | Class | Resume hint | Outcome | UTC |
|---|---|---|---|---|
| none | n/a | n/a | n/a | n/a |

## Test plan
(no test plan section in plan-file)
