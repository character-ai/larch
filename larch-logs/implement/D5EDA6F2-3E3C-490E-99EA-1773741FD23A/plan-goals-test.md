## Goal
Implement issue #3726: [IMPLEMENTING] python/ship.py stall envelope defeats Step 18a recovery (vocab + detail log)\n\n## Context (run E5F45BFF, issue #3704 / PR #3712).

## Implementation Plan
## Context (run E5F45BFF, issue #3704 / PR #3712)

During `/implement --merge --emergency` on #3704, CI failed on PR #3712 (two real, small harness-pin regressions). `python/ship.py` (the default Step 8+ driver) exhausted its outer CI-fix attempts and exited 4 STALLED with JSON `{"detail":"outer fix attempts exhausted","failed_run_id":"27106856703",...}`.

Step 18a stall recovery then classified the stall as `transient-infra` with `RESUME_HINT=none` and never dispatched recovery — the actionable evidence (`failed_run_id` + CI log tail) was discarded, the run terminal-failed (`[STALLED]` rename, low-signal auto-report), and the operator had to fix CI, rebase, push, and merge manually. The auto-filed report for this occurrence was #3717 (superseded by this issue).

## Root cause

The Python driver's persisted stall envelope is too weak for `skills/implement/scripts/stall-recovery-report.sh classify`:

1. `STALL_STEP="outer fix attempts exhausted"` — free text rather than a numeric step token; the classifier sanitizes it to `unknown`.
2. `BAIL_REASON` is left empty — never `ci-fix-exhausted`, so the recoverable class (`ci-fix-exhausted` → `RESUME_HINT=step8-shippr`, retry cap 8) which requires `BAIL_REASON=ci-fix-exhausted` plus a readable detail log can never match on the Python path.
3. No `BAIL_FAILURE_DETAIL_LOG` is persisted — no redacted failing-job log tail, so the evidence-specific classes (`test-failure` / `lint-failure`) cannot match either.
4. Exit-code asymmetry vs the bash contract: `scripts/ship-pr.sh` surfaces in-script CI-fix exhaustion as exit 3 with `BAIL_REASON=ci-fix-exhausted` (which routes to the orchestrator's autonomous main-agent CI-fix sub-procedure in `skills/implement/SKILL.md` Step 8+), while `python/ship.py` exits 4 STALLED for the same shape — so the autonomous CI-fix path is unreachable on the default driver.

Prior art: #3543 (closed) reported the classifier side of this; #3462 / PR #3567 taught `classify` to read `finalize-state.sh` as an evidence surface. That fix is in place and working — but the driver-side vocabulary above still defeats it, because the values the driver persists are not classifier-recognizable tokens.

## Work items (Python side only — per the standing rule, no `scripts/ship-pr.sh` changes)

1. On outer CI-fix exhaustion, persist a numeric CI-loop step token (`STALL_STEP=10` family) and `BAIL_REASON=ci-fix-exhausted` into `ship-pr-state.sh` / `finalize-state.sh` instead of the free-text sentence (keep the human sentence in the JSON `detail` field only).
2. Persist a redacted failing-job log tail and set `BAIL_FAILURE_DETAIL_LOG=<path under the session tmpdir>` before the terminal exit, so `classify` can reach `ci-fix-exhausted` / `test-failure` / `lint-failure` with primary evidence.
3. Decide and align the exit-3-vs-exit-4 contract for CI-fix exhaustion with the SKILL.md Python selector routing (`needs_user_reason=ci-fix-exhausted` on exit 3 → autonomous main-agent CI-fix sub-procedure), so the default Python driver reaches the same recovery surface as the bash opt-in instead of stalling terminally.
4. Tests: pytest coverage in `python/` pinning the persisted envelope (numeric `STALL_STEP`, `BAIL_REASON` enum token, detail-log presence/redaction), plus an acceptance check that `stall-recovery-report.sh classify` on the new envelope yields `ci-fix-exhausted` / `RESUME_HINT=step8-shippr` (not `transient-infra` / `none`).

## Acceptance

- A reproduced outer CI-fix exhaustion on the Python driver classifies as `ci-fix-exhausted` with `RESUME_HINT=step8-shippr` in Step 18a; no more `transient-infra at unknown` auto-reports for this failure shape.
- `make py-lint` + `make py-test` green; affected bash harnesses green.

## Test plan
(no test plan section in plan-file)
