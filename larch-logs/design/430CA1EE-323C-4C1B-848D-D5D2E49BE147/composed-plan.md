## Plan

## Approach

Keep the fix in the repair-loop CLI boundary. Do not change the generic `run_check_fix_loop` status model.

Add a small helper that marks main-agent fallback lint sites:

- `step3`
- `step5-self-review`
- `step5-mav`
- `step6`

When `run_check_fix_loop` returns `no-changes-stale` for one of those sites, synthesize the same ledger fields used by `main-agent-required`:

- site from `_ledger_site_for_lint_site(lint_site)`
- trigger from `_ledger_trigger_for_lint_site(lint_site)`
- step from `_ledger_step_for_site(lint_site)`
- phase from `_ledger_phase_for_site(lint_site)`
- dispatcher `lint-fix-loop`
- exit code `1`
- failure detail log from the validated initial `--checks-log`

Then emit:

- `NEXT_ACTION=main-agent-edit`
- `LOOP_STATUS=no-changes-stale`
- `LINT_FIX_LEDGER_*`

Leave validation failures, missing log failures, ship-pr internal sites, and ordinary exhausted failures on `NEXT_ACTION=stall`.

## Files to modify/create

### UPDATED: python/larch/implement/checks_lint_fix.py

- Change `_repair_loop_action` to consider the lint site, or add a separate helper near it.
- Add a helper that determines whether `no-changes-stale` can fall back to main-agent edits.
- Add a helper to populate `LoopResult` ledger fields for the no-change stale fallback path.
- In `checks_repair_loop_main`, after `run_check_fix_loop` returns and before printing KVs:
  - if `loop.status == "no-changes-stale"` and the site supports main-agent fallback, populate ledger fields from the validated `args.checks_log` **and explicitly set `loop.ledger_ready = True`** — this is required so `_print_loop_ledger` emits `LINT_FIX_LEDGER_READY=true` and stall-recovery can record the escalation;
  - route the action to `main-agent-edit`;
  - keep printing ledger only for `main-agent-edit`.
- Keep `run_check_fix_loop` and `escalate` behavior stable unless tests show another CLI caller needs the new behavior.

### UPDATED: python/tests/implement/test_checks.py

- Update the existing `test_checks_repair_loop_main_stall_exit_is_parseable` or split it into two tests:
  - `step6` no-change stale now returns rc `0`, `NEXT_ACTION=main-agent-edit`, `LOOP_STATUS=no-changes-stale`, and full `LINT_FIX_LEDGER_*`.
  - a non-fallback site, such as `ship-pr-ci-initial`, still returns `NEXT_ACTION=stall` for `no-changes-stale`.
- Add assertions for:
  - `LINT_FIX_LEDGER_READY=true`
  - `LINT_FIX_LEDGER_SITE=step6`
  - `LINT_FIX_LEDGER_TRIGGER=main-agent-required`
  - `LINT_FIX_LEDGER_STEP=6`
  - `LINT_FIX_LEDGER_PHASE=checks`
  - `LINT_FIX_LEDGER_DISPATCHER=lint-fix-loop`
  - `LINT_FIX_LEDGER_EXIT_CODE=1`
  - `LINT_FIX_LEDGER_FAILURE_DETAIL_LOG=<validated checks log>`
- Keep existing unit tests that assert `run_check_fix_loop(...).status == "no-changes-stale"` and `escalate("no-changes-stale")` remains stalled.

### MAY_UPDATE: skills/implement/references/checks-repair-loop.md

- Only update if the implementation changes the documented stdout contract.
- If edited, add one short note that `LOOP_STATUS=no-changes-stale` can pair with `NEXT_ACTION=main-agent-edit` at supported lint sites, and that callers should follow the existing main-agent-edit branch.

## Edge cases

- Invalid `--tmpdir`, unknown `--site`, and invalid `--checks-site` must still emit `NEXT_ACTION=stall`.
- If the original redacted log fails validation, do not synthesize ledger fields.
- Do not route ship-pr CI no-change stale to main-agent edit unless an existing contract already supports that path.
- Preserve `LOOP_STATUS=no-changes-stale` so operators can distinguish this fallback from direct `main-agent-required`.
- Preserve heartbeat `PROGRESS=` lines. Tests should key-scan stdout rather than assume the first line is `NEXT_ACTION`.

## Failure modes when non-trivial

- A broad mapping from all `no-changes-stale` statuses to `main-agent-edit` could change ship-pr CI behavior. Keep the fallback-site allowlist narrow.
- Missing ledger fields would make prompt-side escalation recording fail or silently skip. Assert every ledger key in tests.
- Changing `escalate()` could affect other callers that still treat stale no-change loops as terminal stalls. Avoid that unless a failing test proves it is needed.
- A stale test that expects rc `1` for Step 6 would mask the desired contract. Replace it with both fallback and non-fallback coverage.

## Testing strategy

Run changed Python tests only:

```bash
python3 -m pytest python/tests/implement/test_checks.py -k "repair_loop or no_changes_stale or escalate"
```

Then run the broader changed-file lint path if available:

make py-lint

If docs are edited, run the relevant structure check:

bash scripts/test-implement-structure.sh

## Confidence

High. The bug path is localized to `checks_repair_loop_main` action selection and ledger emission.

## Acceptance

Run changed Python tests only:

```bash
python3 -m pytest python/tests/implement/test_checks.py -k "repair_loop or no_changes_stale or escalate"
```

Then run the broader changed-file lint path if available:

make py-lint

If docs are edited, run the relevant structure check:

bash scripts/test-implement-structure.sh

review_status: ok
rounds_completed: 2
difficulty: MODERATE
diff_lines: 80
