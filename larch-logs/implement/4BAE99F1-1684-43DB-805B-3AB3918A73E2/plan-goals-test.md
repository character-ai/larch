## Goal
Implement issue #7313: [IMPLEMENTING] [BUG] stall-recovery record-escalation rejects Step 2 vendor-failure tokens and drops the escalation; rejection names no offending token.

## Implementation Plan
## Summary

`python3 python/cli.py stall-recovery record-escalation` hard-fails with `token-validation-failed` when invoked during Step 2 vendor-failure handling, so the escalation ledger row is never written and the only durable trace is a self-reported Tool Failure. The rejection message does not say WHICH token (kind or value) failed validation, so committed logs cannot be used to diagnose the caller. This happened in 4 of the last 50 committed `/implement` runs.

## Evidence (committed run logs)

Each of these runs contains a `## Tool Failure: record-escalation` entry with `helper: python/cli.py stall-recovery record-escalation` and `reason: token-validation-failed` in `larch-logs/implement/<RUN>/execution-issues.ndjson`:

| Run | Tracking issue | UTC | Context in the same run |
|---|---|---|---|
| `D3637FD5-DF7F-4DF7-9E41-AF7ED6469419` | #7114 | 2026-07-12T23:06:37Z | Step 2 dispatcher killed by Bash timeout, no envelope |
| `BB1350EF-5DC0-499E-94F3-8118594F155B` | #7116 | 2026-07-12T22:36:14Z | Step 2 cursor-implement failed (exit 1, non-auth) |
| `6EF99043-47FA-4981-8E8E-5DA9CC17B7EF` | #7061 | 2026-07-12T18:16:10Z | Step 2 cursor-implement failed (exit 124, timeout) |
| `43A3ED2E-96F7-4A19-A63A-44814B8D936A` | #7023 | 2026-07-12T07:31:25Z | Step 2 Codex bailed: quota |

All four correlate with Step 2 vendor failures. The appended Tool Failure records contain only the reason token; no kind, no value.

## Root cause (file:line, current main)

- `python/larch/state/_escalation.py::record_escalation`:
  - lines ~122-124: `if not _safe_token(kind="site", ...) or not _safe_token(kind="trigger", ...)` prints the generic `stall-recovery: record-escalation token validation failed` and returns `hard_fail("token-validation-failed")`.
  - lines ~125-127: the same generic message and reason for the step/phase pair.
  - `hard_fail` appends the Tool Failure via `_append_record_escalation_tool_failure(tmpdir=..., reason=...)` and returns 1 BEFORE the ledger write (`stall-recovery-escalation-ledger.tsv`, line ~130). The escalation is lost.
- `python/larch/state/_tokens.py::_safe_token` (line ~275+) validates against fixed sets:
  - `_COMMON_SITES` (lines 61-65): `step3, step5, step5-self-review, step5-mav, step6, step8, step18a, review-loop, lint-fix-loop, ship-pr, ship-pr-ci-initial, ship-pr-ci-merge, ship-pr-ci-per-job, ship-pr-internal, recovery-inline`. **There is no Step 2 site token.**
  - `_COMMON_TRIGGERS` (lines 72-76): includes owner tokens such as `step2-impl`, plus `fix-attempts-exhausted`, `all-vendors-failed`, etc. Vendor bail reasons such as `cursor-runtime-failure` or `quota` are NOT in the set.
  - `_COMMON_PHASES` (line 93) does include `step2` and `implementation`.

Inference (to confirm while fixing): the orchestrator, following the Step 2 `STATUS=bailed` branch (`skills/implement/SKILL.md` line ~356: log the bail, set `STALL_STEP=2`, `PHASE=implementation`, bail to Step 12d) and the stall-recovery guidance (`skills/implement/references/stall-recovery.md` item 6), calls record-escalation with a site of `step2` (not a legal site) or passes the vendor bail reason as `--trigger` (not a legal trigger). Either rejection produces exactly the observed failure. The observability gap (no kind/value in the message) is why this needs confirmation at all; fixing that gap is part of this issue.

## Expected behavior

- A Step 2 vendor-failure escalation recorded with the documented tokens writes a ledger row and exits 0.
- When validation does reject, the stderr line and the appended Tool Failure entry name the failing kind and a sanitized value, for example `reason=token-validation-failed kind=site value=step2`, so a committed log alone is enough to diagnose the caller.

## Observed behavior

- The escalation is dropped, `hard_fail` appends a Tool Failure with only `reason: token-validation-failed`, and downstream consumers (escalation-success checks in `python/larch/state/_report.py`, which look for ledger/fallback/marker files and the tagged Tool Failure) see a failed recording instead of a handoff record.

## Suggested fix (ordered)

1. **Diagnosability first**: in `record_escalation`, split the two combined validation branches so each `_safe_token` failure reports its own kind, and include kind plus sanitized value in both the stderr message and the appended Tool Failure entry text. Sanitize the value with the existing token sanitizers before embedding (`_tokens.py` helpers); truncate to a bounded length.
2. **Reproduce the caller**: trace the exact record-escalation invocation used for Step 2 vendor bails (start from `skills/implement/SKILL.md` line ~356 and `skills/implement/references/stall-recovery.md` item 6; also check `skills/implement/references/checks-repair-loop.md` line ~73 which forwards `LINT_FIX_LEDGER_*` values). Reproduce the rejection in a unit test with the exact argv.
3. **Close the gap**: either (a) add the missing legal tokens to `python/larch/state/_tokens.py` (a `step2` site, and any legitimately-used trigger owner token; `step2-impl` already exists in `_COMMON_TRIGGERS`), or (b) correct the documented caller guidance so Step 2 escalations always pass tokens from the legal sets. Prefer (a) plus (b): make `step2` a legal site because Step 2 escalations are real, and tighten the skill text to name the exact tokens to pass (site, trigger, step, phase) for the Step 2 vendor-bail case.
4. **Regression tests (G-Fix-2)** in `python/tests/state/test_stall_recovery.py` (or the module that covers `_escalation.py`):
   - replay the Step 2 vendor-failure escalation with the documented tokens and assert a ledger row is written and exit code is 0;
   - assert the rejection diagnostic names kind and sanitized value in stderr and in the appended execution-issues entry;
   - keep an existing-behavior test that a genuinely illegal token still hard-fails (fail-closed preserved).
5. **Class audit**: scan `larch-logs/implement/*/execution-issues.ndjson` for `record-escalation` Tool Failures and confirm every observed instance is explained by the fixed caller (the four runs above are the known set in the last 50 runs).

## Acceptance criteria

- The four-run reproduction argv (from step 2 of the fix) exits 0 and writes a ledger row on the fixed branch.
- Rejection messages include kind and sanitized value; a test pins the format.
- `make py-lint` and `make py-test` pass; no other `record-escalation` call site regresses (grep `record-escalation` across `skills/` and `python/` and re-check each caller's tokens against the final legal sets).

## Affected files

- `python/larch/state/_escalation.py`
- `python/larch/state/_tokens.py`
- `skills/implement/SKILL.md` and/or `skills/implement/references/stall-recovery.md` (caller token guidance)
- `python/tests/state/` (regression tests)

## Related work (do not duplicate)

- #5604 (DONE) fixed record-escalation rejecting its own `--failure-detail-log`; #5021 (DONE) fixed a wrong trigger token from Step 18a transient-infra reship. Both are different tokens and different callers; neither added kind/value diagnostics nor a Step 2 site.

## Test plan
(no test plan section in plan-file)
