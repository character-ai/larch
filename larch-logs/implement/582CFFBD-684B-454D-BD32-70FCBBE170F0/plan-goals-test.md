## Goal
Move Report to end of audit-report title bracket so the generic [... Report] filter matches it

## Implementation Plan
## Goal
Move "Report" to end of bracket in audit-report titles so the generic `[... Report]` filter in `find-lock-issue.sh` (`has_report_prefix`) matches them, making the dedicated `has_run_logs_audit_report_title` guard redundant.

## New title format
`[Run Logs Audit <timestamp> Report] PRs ...` (timestamp before "Report")


### 1. `.claude/skills/audit-runs/scripts/audit-title.sh`
- Lines 5-7 (header comments): Change `[Run Logs Audit Report <ts>]` → `[Run Logs Audit <ts> Report]`
- Line 10 (output comment): Change `TITLE=[Run Logs Audit Report <ts>]` → `TITLE=[Run Logs Audit <ts> Report]`
- Lines 49, 59, 69 (printf calls): Swap `Report %s` → `%s Report` in every `[Run Logs Audit Report %s]` format string

### 2. `.claude/skills/audit-runs/scripts/audit-title.md`
- Lines 8-9 (Output KV examples): Update both TITLE= examples to `[Run Logs Audit <timestamp> Report] PRs #X-#Y` etc.

### 3. `.claude/skills/audit-runs/SKILL.md`
- Line 105 (anti-recursion regex): Change `^\[Run Logs Audit Report` → `^\[Run Logs Audit .* Report\]`

### 4. `.claude/skills/audit-runs/scripts/test-audit-runs.sh`
- `title_matches_audit_report_exclusion` function body (line 367): Change `^\[Run Logs Audit Report` → `^\[Run Logs Audit .* Report\]`
- Test 14/14b fixture titles (lines 369, 371): Change to `[Run Logs Audit 2026-05-20T12:30-07:00 Report] PRs ...`
- Test 14e (line 384-385): The assertion flips from `no_match` to `matched` because `has_report_prefix` now WILL match the new title shape (it ends with ` Report]`). Update the assertion and its description.
- Lines 890, 893, 896, 899: Update all `audit-title.sh` output fixture assertions from old to new shape
- Lines 1396, 1398: Same
- Line 1881: Update jq regex `test("^\\[Run Logs Audit Report")` → `test("^\\[Run Logs Audit .* Report\\]")`
- Lines 1892, 1894: Update fixture title strings passed to `classify_c1_bucket_from_gh_issues_json`

### 5. `.claude/skills/audit-runs/scripts/test-audit-runs.md`
- Line 20: Update the note about the existing `has_report_prefix` not matching old audit-report titles — it WILL now match.

### 6. `skills/fix-issue/scripts/find-lock-issue.sh`
- Remove the `has_run_logs_audit_report_title` function (lines ~155-166) entirely
- Remove the call at line ~635 (`if has_run_logs_audit_report_title...`), relying solely on `has_report_prefix` + `audit-report` label filter
- Update the comments that explain why the secondary guard existed (lines ~155-159)

### 7. `skills/fix-issue/scripts/test-find-lock-issue.sh`
- Line 919: Change fixture title `[Run Logs Audit Report 2026-05-20T19:30Z] PRs #2430-#2440` → `[Run Logs Audit 2026-05-20T19:30Z Report] PRs #2430-#2440`


## Test plan
- `make lint` (runs offline test harnesses: `test-audit-runs.sh`, `test-find-lock-issue.sh`)
