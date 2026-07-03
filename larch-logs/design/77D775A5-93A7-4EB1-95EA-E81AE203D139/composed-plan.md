## Plan

## Approach

Use the existing normalization seam. `dedup_tier_a_report()` already writes the cross-repo helper stdout to an env file, but then re-emits raw `FILE_FAILURE_REPORT_*` keys. Replace that final emit with `normalize_file_failure_report_env(...)` so callers receive `STALL_RECOVERY_REPORT_*`.

Keep the scope narrow. Do not change `scripts/file-failure-report-cross-repo.sh` or `design_terminal.py`.

## Files to modify/create

### UPDATED: python/larch/state/_report.py

- In `dedup_tier_a_report()`, replace `_emit_env_file(out)` with a direct call to `normalize_file_failure_report_env(argparse.Namespace(...))`.
- Pass `implement_tmpdir=str(tmpdir)` and `file_failure_report_env=str(out)`.
- Preserve the existing helper invocation, slice handling, and fallback paths.
- Do not alter Tier B `_emit_chat_print_filing_status()`, which already uses the same normalizer.

### UPDATED: python/tests/state/test_stall_recovery.py

- Add a regression test for `dedup_tier_a_report_main`.
- Build a minimal tmpdir with:
  - an in-tmpdir body file
  - a fake `CLAUDE_PLUGIN_ROOT/scripts/file-failure-report-cross-repo.sh`
- Mock `subprocess.run` so:
  - the `gh repo view` call returns `owner/repo`
  - the helper call writes realistic raw stdout such as `FILE_FAILURE_REPORT_STATUS=dedup-comment` and `FILE_FAILURE_REPORT_URL=...`
- Assert stdout contains:
  - `STALL_RECOVERY_REPORT_STATUS=dedup-comment`
  - `STALL_RECOVERY_REPORT_URL=...`
  - issue URL and issue number aliases when the URL is an issue URL
- Assert stdout does not contain raw `FILE_FAILURE_REPORT_STATUS=`.
- Keep the existing prefixed-slice test unchanged unless the new assertion can fit cleanly there without reducing clarity.

## Edge cases

- Helper emits an unknown status: the normalizer should convert it to `fallback-print-required` with the existing missing-status fallback behavior.
- Helper emits `no-match` or `lookup-failed-open`: those must remain pass-through statuses so `design_terminal.py` can continue Tier A filing or fallback.
- Helper emits a dedup-comment URL: the canonical URL should be emitted, and issue aliases should appear only when `_issue_url_number()` recognizes an issue URL.
- Dry-run and helper-missing paths already emit canonical keys and should not change.

## Failure modes

- If normalization is skipped, `/design` continues seeing an empty `STALL_RECOVERY_REPORT_STATUS` and reports `tier-a-dedup-status-unexpected`.
- If the new test mocks the wrong subprocess module, it may accidentally call real `gh`. Patch the shared `subprocess.run` object already used by the existing tests.
- If the helper stdout file is outside the tmpdir, normalization fails closed. The current path is inside the tmpdir, so the plan preserves that invariant.

## Testing strategy

- Run the focused regression test:
  - `python3 -m pytest python/tests/state/test_stall_recovery.py -k "dedup_tier_a_report"`
- Run Python lint on changed files:
  - `python3 -m ruff check python/larch/state/_report.py python/tests/state/test_stall_recovery.py`
- If available in the environment, run pyright on the changed Python files or the repo's changed-file relevant checks path.

## Acceptance

- Run the focused regression test:
  - `python3 -m pytest python/tests/state/test_stall_recovery.py -k "dedup_tier_a_report"`
- Run Python lint on changed files:
  - `python3 -m ruff check python/larch/state/_report.py python/tests/state/test_stall_recovery.py`
- If available in the environment, run pyright on the changed Python files or the repo's changed-file relevant checks path.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
diff_lines: 45
