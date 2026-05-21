## Goal
Remove oos-issues.ndjson from required-files TSV to stop false failures in required-file-presence scan

## Implementation Plan

Remove `oos-issues.ndjson` from the required-files set (path 2 of issue #2522).

The file is only written by `larch-log.sh append --batch oos-issues` when OOS items
exist. Most runs have no OOS items so the file is absent, causing the
`required-file-presence` audit scan to fail on every recent run.

### Files to change

1. **`docs/run-logs-required-files.tsv`** — remove the line:
   ```
   oos-issues.ndjson	step9a1	oos-issues	ndjson
   ```

2. **`scripts/test-verify-run-log-completeness.sh`** — remove two assertions
   that expect `oos-issues.ndjson` to appear in MISSING output:
   - `assert_contains "pr-number-only requires oos issues" "$out" "oos-issues.ndjson"`
   - `assert_contains "done-status requires oos issues" "$out" "oos-issues.ndjson"`

3. **`.claude/skills/audit-runs/scripts/audit-scan-run.md`** — update the
   example `required-file-presence` output line (line 12) to not list
   `oos-issues.ndjson` as missing.

4. **`docs/run-logs.md`** — update the `### run-statistics.md` section's
   "**Written**: Step 9a.1 alongside `oos-issues`." line to remove the
   "`alongside oos-issues`" reference.

### What NOT to change

- Keep `oos-issues.ndjson` in the `step9a1` `condition_reached` OR-checks in
  both `scripts/verify-run-log-completeness.sh` and
  `.claude/skills/audit-runs/scripts/audit-scan-run.sh` (backward compat).
- Keep the `### oos-issues.ndjson` section in `docs/run-logs.md` — the file
  is a valid optional artifact when OOS items exist.
- Do NOT change `docs/run-logs.md` line 27 (file tree listing) — the file is
  still a real optional artifact.


## Test plan

Run `make test-verify-run-log-completeness` and `make lint` to confirm the
tests pass and linters are clean.
