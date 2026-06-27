## Goal
Implement issue #5619: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] Truncated sidecar evidence is not consumed by classify or Tier A compose-report.

## Implementation Plan
## Plan

## Approach

Add a small, shared sidecar lookup path in stall recovery.

- Keep `--failure-detail-log` as the primary source.
- When that path is invalid, look for a safe `failure_detail_log=` value in the escalation ledger.
- Validate and read the sidecar with the same tmpdir, symlink, regular-file, and 64 KiB checks.
- Store the resolved absolute sidecar path in `FAILURE_DETAIL_LOG` when classify uses it.
- Use the same fallback in Tier A report composition so auto-filed reports include the truncated lint-fix evidence.

## Files to modify/create

### UPDATED: python/larch/state/stall_recovery.py

- Add a private helper that reads `failure_detail_log=` fields from escalation rows.
  - Parse tab-separated `key=value` fields.
  - Ignore empty, missing, or unsafe values.
  - Treat ledger values as tmpdir-relative paths.
  - Validate the resolved path with existing failure-detail-log checks.
  - Prefer the most recent usable row.
- Add a private helper that reads the primary failure-detail log first, then falls back to sidecar candidates from:
  - `_DEFAULT_ESCALATION_LEDGER`
  - `_DEFAULT_ESCALATION_FALLBACK`
  - prefixed equivalents when `--artifact-prefix` is set.
- Update `classify()`:
  - Replace direct `_read_validated_failure_detail_log()` use for `args.failure_detail_log`.
  - If the original path is oversize but a ledger sidecar is valid, classify from the sidecar content.
  - Emit `FAILURE_DETAIL_LOG=<absolute-sidecar-path>` for the consumed sidecar.
- Update `_classify_generic_from_terminal_state()` the same way for prefixed generic artifacts.
- Update `_compose_tier_a_issue()`:
  - Read classification `FAILURE_DETAIL_LOG` first.
  - If it is invalid or empty, fall back to the ledger sidecar.
  - Append `## Validated failure-detail log` when the sidecar is valid.
- Avoid changing record-escalation behavior.
- Avoid widening accepted external paths.

### UPDATED: python/test_stall_recovery.py

- Add a classify regression test:
  - Create an oversize failure log whose prefix contains lint/test failure evidence.
  - Call `record_escalation_main()` so it materializes a truncated sidecar in the ledger.
  - Call `classify_main()` with the original oversize `--failure-detail-log`.
  - Assert classify uses the sidecar evidence and emits the sidecar path, not the oversize path.
- Add a Tier A compose-report regression test:
  - Create a classification env that points at the original oversize path.
  - Create a ledger sidecar via `record_escalation_main()`.
  - Render `compose_report_main(... --surface issue-input ...)`.
  - Assert the output contains `## Validated failure-detail log` and sidecar evidence.
- Keep existing oversize rejection tests.
  - They should still pass when no ledger sidecar exists.

## Edge cases

- Ledger row exists but the sidecar is missing: ignore it.
- Ledger row points outside tmpdir: ignore it.
- Ledger row points to a symlink: ignore it.
- Ledger has several rows: use the newest valid sidecar.
- Original detail log is valid: use it and do not consult the sidecar.
- No `--failure-detail-log` and no classification detail value: do not invent evidence unless a report render explicitly has ledger sidecar evidence.

## Failure modes

- If all candidates fail validation, preserve current behavior.
- If a sidecar read fails after validation, omit the detail evidence.
- If prefixed generic artifacts are used, only prefixed ledger and fallback files should affect that generic classification.

## Testing strategy

Run targeted tests:

```bash
python3 -m pytest python/test_stall_recovery.py -k "failure_detail_log or record_escalation_truncates_oversize_detail_log or compose_report_tier_a"
```

Run targeted lint/type checks for changed Python files:

```bash
python3 -m ruff check python/larch/state/stall_recovery.py python/test_stall_recovery.py
python3 -m pyright python/larch/state/stall_recovery.py python/test_stall_recovery.py
```

## Acceptance

Run targeted tests:

```bash
python3 -m pytest python/test_stall_recovery.py -k "failure_detail_log or record_escalation_truncates_oversize_detail_log or compose_report_tier_a"
```

Run targeted lint/type checks for changed Python files:

```bash
python3 -m ruff check python/larch/state/stall_recovery.py python/test_stall_recovery.py
python3 -m pyright python/larch/state/stall_recovery.py python/test_stall_recovery.py
```

diff_added: 110
diff_deleted: 10
mechanical_churn: false
diff_lines: 120

## Test plan
(no test plan section in plan-file)
