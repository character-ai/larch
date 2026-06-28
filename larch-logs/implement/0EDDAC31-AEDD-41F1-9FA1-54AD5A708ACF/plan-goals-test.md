## Goal
Implement issue #5719: [IMPLEMENTING] [Bug] /implement escalation: Codex implementation: NamedTemporaryFile not cleaned up on FileNotFoundError return path (ship-pr:first-fixer-non-health).

## Implementation Plan
<!-- larch-stall:signature=b5d26a6b76b60fbc27885b587a33299f84cd05a1d5436618e6424515f84886fe -->
## Report metadata
- **Report kind**: `escalation-success`
- **Failure class**: ``
- **Step**: `unknown`
- **Bail reason**: `redacted`
- **Run ID**: `CB3FB57C-0A4B-4059-B843-4AB840D3C51F`
- **Branch**: `unknown`
- **PR URL**: `https://github.com/character-ai/larch/pull/5716`

## Root-cause finding

verdict=larch-defect
confidence=high
summary=Codex implementation: NamedTemporaryFile not cleaned up on FileNotFoundError return path

The CI test `test-voter-calibration` failed because `voter-calibration.py` (new code from Codex) leaked a `NamedTemporaryFile` when `fetch_main()` raised `FileNotFoundError`. The `return _realized_outcomes_skip("gh_unavailable")` inside the `except FileNotFoundError` handler exited before entering a separate `try/finally` cleanup block, leaving a `voter-calibration-issues-*.json` file in `TMPDIR`. Fix: merged the two separate `try` blocks into one outer `try/finally` so the `Path(dump_path).unlink()` cleanup always runs.



## Attempts

| Attempt | Class | Resume hint | Outcome | UTC |
|---|---|---|---|---|
| none | n/a | n/a | n/a | n/a |

## Escalation ledger

utc=2026-06-28T02:38:43.140244+00:00	site=ship-pr	trigger=first-fixer-non-health	step=8	phase=ci-initial	dispatcher=ship-pr	exit_code=3	failure_detail_log=

## Test plan
(no test plan section in plan-file)
