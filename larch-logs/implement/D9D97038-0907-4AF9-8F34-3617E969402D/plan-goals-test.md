## Goal
Implement issue #6231: [IMPLEMENTING] /design escalation: design escalation reached main-agent recovery (step3-review:main-agent-apply-required).

## Implementation Plan
## Plan

Approach

- Define one allowlist, `STEP3_ESCALATION_FAILURE_STATUSES = (panel-failed, panel-init-failed, tally-error, degraded-empty-collector)`, as the only Step-3 statuses that create escalation-success evidence. The three normal handoffs (`main-agent-apply-required`, `main-agent-vote-required`, `postplan-operator-required`) are simply "not in the allowlist"; no separate handoff tuple is added.
- Fix at the source: `step3_record_report_evidence` records a ledger row only for allowlisted genuine failures, so no caller writes normal-handoff rows.
- Fix at the report gate: `escalation_evidence_present()` treats a ledger/fallback row as evidence UNLESS it is a `site=step3-review` row whose `trigger=` is a normal handoff. It scans every row, so validator-autofix rows and genuine Step-3 failures still count; only step3 handoff-only ledgers are neutralized.
- Keep `record-failure-marker` and `execution-issues.md` tool-failure evidence loud; genuine-failure reporting is unchanged.

Files to modify/create

### UPDATED: python/larch/core/config.py

- Add one `Final` tuple constant near related token/config literals:
  - `STEP3_ESCALATION_FAILURE_STATUSES = ("panel-failed", "panel-init-failed", "tally-error", "degraded-empty-collector")` — the only Step-3 statuses that count as escalation-success evidence.
- This single allowlist is consumed by both the recorder and the report gate; the normal-handoff set already exists as `_STEP3_INTERACTIVE_STATUSES` in `plan_review_normalize.py`, so do NOT add a separate `STEP3_NORMAL_HANDOFF_STATUSES` tuple (would be unused/dead config that can drift from the interactive set).
- Keep tuple order stable and human-readable. Do not move unrelated config.

### UPDATED: python/larch/review/plan_review_normalize.py

- Import `STEP3_ESCALATION_FAILURE_STATUSES` from `larch.core.config`.
- Replace the current `_STEP3_EVIDENCE_STATUSES` contents with `set(STEP3_ESCALATION_FAILURE_STATUSES)` — drops the three normal handoffs, keeps the four genuine failures.
- Keep normal-handoff statuses in `_STEP3_STATUS_VALUES`, `_STEP3_LOOP_STATUS_VALUES`, `_STEP3_INTERACTIVE_STATUSES`, and `_STEP3_NEXT_ACTION_BY_STATUS` unchanged — routing must not change.
- In `step3_record_report_evidence`, drop the three normal handoffs from the inline status→phase map so the recorder returns `0` (no-op) for them regardless of caller. This is load-bearing because `step3_loop_emit_envelope` (plan_review_loop.py:145) and the `--record-report-evidence` CLI call the recorder directly, not gated by `_STEP3_EVIDENCE_STATUSES`. After the change only the four genuine failures map to a phase (all `validation`; `postplan-operator-required`'s `postplan` phase is removed with it).
- Preserve the existing warning behavior when genuine-failure evidence recording fails.

### UPDATED: python/larch/design/design_terminal.py

- Add a small helper near `failure_report_core` (e.g. `_ledger_file_has_escalation_evidence(path)`) that reads a ledger-like TSV file row by row and returns true when ANY row is evidence. A row is evidence when:
  - its `site=` is NOT `step3-review` (e.g. validator-autofix rows: `dispatcher=design-step-validator-autofix`, `step=validator`), OR
  - its `site=` is `step3-review` AND its `trigger=` is in `config.STEP3_ESCALATION_FAILURE_STATUSES`.
  It MUST iterate every row (not just the first), so a legacy step3 handoff row preceding a genuine `tally-error` row — or preceding a validator-autofix row — still counts.
- This narrow, site-scoped filter suppresses ONLY step3-review normal-handoff rows; it must NOT drop other design escalation rows (validator-autofix), which remain valid escalation-success evidence.
- Update `escalation_evidence_present()`:
  - Count the ledger or fallback file as evidence only when the row-scanning helper returns true (replaces the current non-empty-size check on `ledger`/`fallback`).
  - Keep the non-empty `record-failure-marker` branch as evidence.
  - Keep the tagged `Tool Failure: record-escalation` in `execution-issues.md` branch as evidence.
- Net effect: legacy step3 handoff-only ledger/fallback rows stop triggering future `escalation-success` reports; mixed ledgers with at least one genuine-failure or non-step3 row still report; genuine failures and validator-autofix escalations unchanged.

### UPDATED: python/tests/review/test_plan_review.py

- Add a test that `step3_record_report_evidence` is a no-op for `main-agent-apply-required`, `main-agent-vote-required`, and `postplan-operator-required`: monkeypatch `subprocess.run` to raise if called, and assert no ledger, fallback, marker, or `.step3-report-*.recorded` sentinel is created.
- Add or update a genuine-failure assertion so `tally-error` or `panel-failed` still attempts recording (the phase map still contains it).

### UPDATED: skills/design/scripts/test-design-step3-review.sh

- The `assert_escalation_recorded` loop currently asserts all seven Step-3 statuses record an escalation ledger row and would fail once the recorder stops recording handoffs. Split it:
  - Keep `assert_escalation_recorded` (phase `validation`) for the four genuine failures: `panel-failed`, `panel-init-failed`, `degraded-empty-collector`, `tally-error`.
  - Add `assert_escalation_not_recorded` for the three normal handoffs (`main-agent-vote-required`, `main-agent-apply-required`, `postplan-operator-required`): run `plan-review run --record-report-evidence "$status"` and assert NO `design-failure-escalation-ledger.tsv`, fallback, marker, or `.step3-report-*.recorded` sentinel is created.
  - Remove `postplan-operator-required` from the `phase=postplan` recorded assertion.
- Update the harness `pass` message text accordingly, and keep the sibling `skills/design/scripts/test-design-step3-review.md` contract summary in sync.

### UPDATED: python/tests/design/test_design_lifecycle.py

- Change the existing `test_failure_report_escalation_success_from_ledger` fixture from `main-agent-vote-required` to a genuine-failure trigger (`tally-error` or `panel-failed`).
- Also update `test_failure_report_escalation_tier_a_backfill_failures_are_specific`: it currently seeds `trigger=main-agent-vote-required` and asserts the tier-A `fallback-print-required` branches on `outcome=approved`. Switch its ledger trigger to a genuine failure so it still exercises the tier-A path after the gate change. Sweep every `failure_report_escalation*` fixture that seeds `design-failure-escalation-ledger.tsv` with a handoff trigger and retarget it.
- Add a parametrized normal-only-ledger test for `main-agent-apply-required`, `main-agent-vote-required`, `postplan-operator-required`: an approved outcome skips reporting with `DESIGN_FAILURE_REPORT_DECISION=skip` and `DESIGN_FAILURE_REPORT_REASON=no-escalation-evidence`.
- Add a mixed-ledger test: two rows, a step3 normal-handoff row followed by a genuine-failure row (`tally-error`), asserting the approved run still reports (`DESIGN_FAILURE_REPORT_DECISION=escalation-success`).
- Add a validator-autofix regression test: seed a ledger row with a non-`step3-review` site (`dispatcher=design-step-validator-autofix`, `step=validator`) and assert an approved run still reports `escalation-success` (the site-scoped gate keeps non-step3 rows).
- Add a malformed / no-`trigger` ledger test asserting it skips with `DESIGN_FAILURE_REPORT_REASON=no-escalation-evidence`.
- Add a fallback-file variant mirroring the ledger cases, since the helper scans fallback rows the same way.

Edge cases

- A ledger/fallback file may contain mixed rows; the gate reports when ANY row is evidence (the helper scans every row, not just the first).
- Non-`step3-review` escalation rows (validator-autofix) always count as evidence, regardless of trigger.
- A malformed ledger with no parseable `trigger=`/`site=` does not count as escalation evidence.
- A non-empty `record-failure-marker` still counts (a genuine failed attempt to record escalation evidence).
- `execution-issues.md` with a `Tool Failure: record-escalation` entry still counts.

Failure modes

- Removing handoffs from the wrong status set (`_STEP3_STATUS_VALUES`, `_STEP3_LOOP_STATUS_VALUES`, `_STEP3_INTERACTIVE_STATUSES`, `_STEP3_NEXT_ACTION_BY_STATUS`) would break Step 3 next-action routing. Touch only `_STEP3_EVIDENCE_STATUSES` and the recorder phase map.
- If the gate filtered by `trigger` regardless of `site`, it would drop legitimate validator-autofix escalation rows and skip real escalation-success reports. Scope the filter to `site=step3-review` rows only.
- If the all-rows helper stops at the first row, a legacy handoff row before a genuine-failure or validator-autofix row would suppress a real report.

Testing strategy

- Targeted:
  - `python3 -m pytest python/tests/review/test_plan_review.py -k 'record_report_evidence or step3_normalizer_escalation'`
  - `python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'failure_report_escalation'`
  - `make test-design-step3-review`
- If those selectors miss renamed tests, run the two full files:
  - `python3 -m pytest python/tests/review/test_plan_review.py`
  - `python3 -m pytest python/tests/design/test_design_lifecycle.py`
- Run lint on changed Python files: `make py-lint`.

## Acceptance

- A successful `/design` run whose only Step-3 escalation-ledger evidence is a normal handoff (`main-agent-apply-required`, `main-agent-vote-required`, `postplan-operator-required`) files NO `escalation-success` GitHub issue; the teardown gate skips with `DESIGN_FAILURE_REPORT_REASON=no-escalation-evidence`.
- `step3_record_report_evidence` writes no ledger / fallback / marker / `.step3-report-*.recorded` artifacts for the three normal handoffs, and still records for the four genuine failures (`panel-failed`, `panel-init-failed`, `tally-error`, `degraded-empty-collector`).
- `escalation_evidence_present()` still returns true for genuine Step-3 failures, validator-autofix rows (`site != step3-review`), a non-empty `record-failure-marker`, and `execution-issues.md` record-escalation tool failures; a mixed ledger with at least one genuine/non-step3 row still reports.
- Step 3 next-action routing is unchanged (`_STEP3_STATUS_VALUES`, `_STEP3_LOOP_STATUS_VALUES`, `_STEP3_INTERACTIVE_STATUSES`, `_STEP3_NEXT_ACTION_BY_STATUS` untouched).
- `make test-design-step3-review`, `python/tests/review/test_plan_review.py`, and `python/tests/design/test_design_lifecycle.py` pass, including the new normal-handoff no-op, mixed-ledger, validator-autofix, and malformed/no-trigger cases.
- `make py-lint` passes on changed Python files.

diff_lines: 200

## Test plan
(no test plan section in plan-file)
