## Goal
Fix review panel: drop Reviewer finding catchall in collect-findings.sh and add Claude voter diagnostic logging

## Implementation Plan

Fix two defects in the review panel: (1) the "Reviewer finding" catchall in
collect-findings.sh, and (2) missing diagnostic logging for the Claude voter
in dispatch-code-voters.sh.

### Fix 1 — drop empty-title rows in collect-findings.sh (issue §2b)

File: `skills/review/scripts/collect-findings.sh`

In `parse_output()`, the awk `flush()` function at line 219 substitutes
`"Reviewer finding"` when `title == ""`. This means any reviewer output that
contains only narrative prose (no `- item` or `1. item` lines) gets a phantom
finding row in the ballot.

**Change**: in `flush()`, guard with `if (title != "")` — only print a finding
row when a title was captured. Skip the row silently when `title == ""`.

The skip is silent at the awk level. After `parse_output()` returns, the
`per_tmp` file may be empty or shorter than expected; the existing code path
already handles empty `per_tmp` (lines 288-297 check `[[ ! -s "$per_tmp" ]]`
for Claude files; external files go through `collect-agent-results.sh` which
emits `STATUS=NOT_SUBSTANTIVE`). No special COLLECTOR_STATUS line is needed
in the awk output itself — the downstream counting in the `while IFS=$'\t'
read -r` loop at line 305 naturally produces FINDINGS_COUNT=0 when the
per-reviewer output is all-empty-title.

Also update the sibling `.md`.

### Fix 2 — Claude voter diagnostic logging in dispatch-code-voters.sh (issue §2a)

File: `scripts/dispatch-code-voters.sh`

After lines 77-78 (`voter1_rc=$?` / `.done` write), add a diagnostic block:
when `voter1_rc != 0` OR `! -s "$VOTER_1_PATH"`, log to
`LARCH_EXECUTION_ISSUES_LOG` (or `$REVIEW_TMPDIR/execution-issues.md`
fallback) via `append-tool-failure.sh`:
- Capture `voter1_rc`, output of `wc -c "$VOTER_1_PATH"`, and first 200
  bytes of `"$VOTER_1_PATH.diag"` (if the file exists) into a temp diag file.
- Call `append-tool-failure.sh --category Warnings --site
  "dispatch-code-voters.sh voter1"`.

The diagnosis path should be guarded with `set +e` / `set -e` and `|| true` so
logging failures never abort the dispatch.

Also update the sibling `.md`.

### Fix 3 — Regression cases in test-collect-findings.sh

File: `skills/review/scripts/test-collect-findings.sh`

Add a test case:
- Input: a reviewer output that contains only narrative text (no `- item`
  lines), e.g. `"Gathering the diff and reviewing changes..."`.
- Assert: `FINDINGS_COUNT=0` (no "Reviewer finding" row produced).

### Files to modify

1. `skills/review/scripts/collect-findings.sh` — Fix 1 (awk guard)
2. `skills/review/scripts/collect-findings.md` — Fix 1 sibling doc update
3. `scripts/dispatch-code-voters.sh` — Fix 2 (diagnostic logging)
4. `scripts/dispatch-code-voters.md` — Fix 2 sibling doc update
5. `skills/review/scripts/test-collect-findings.sh` — Fix 3 (regression test)

### Testing strategy

After implementation, run `/relevant-checks` which invokes:
- `pre-commit` (shellcheck on modified `.sh` files)
- `make test` / agent-lint harnesses including `test-collect-findings.sh`

## Test plan
(no test plan section in plan-file)
