## Goal
Implement issue #6322: [IMPLEMENTING] [OOS] Em-dash scrub follow-up: 7 remaining surfaces from PR #6312 / issue #6293.

## Implementation Plan
## Plan

## Approach

Make the minimum scoped readability fixes from the approved outline.

- Replace remaining user-facing separator strings with colon wording.
- Keep timing-ledger labels unchanged. They are wire labels.
- Keep mock `[content truncated ... safety]` fixtures unchanged. Their assertions only check the prefix.
- Update the offline final-report harness and docs to match the renderer's current `: ` heading contract.
- Harden stalled-summary detection by scanning all lines for a stalled H2, instead of only the first non-empty line.

## Files to modify/create

### UPDATED: python/larch/implement/ci_monitor.py

Change `collect_failed_logs()` so its CI log pointer matches `python/larch/git/gh.py`:

- Use `--- CI log (run {run_id}, repo {repo}): last {tail_lines} lines shown. ...`.
- Do not refactor the helper or call path.

### UPDATED: python/tests/implement/test_ci_monitor.py

Tighten `test_collect_failed_logs_redacts_tail()` so it asserts the colon banner shape, not only `last 100 lines`.

### UPDATED: python/larch/core/redact.py

Change `_UNTERMINATED_MARKER` to use a colon separator in the truncation marker.

Keep the fail-closed behavior unchanged.

### UPDATED: python/tests/core/test_redact.py

Add or adjust an assertion in the unterminated PEM test so the marker contains the new colon wording.

### UPDATED: python/larch/state/bootstrap.py

Change the `_append_failure_with_entry_fallback()` fallback entry title to use a colon after `Step {site}` instead of the old separator.

Do not change timing marks such as `Step 0 ... preflight`.

### UPDATED: python/tests/state/test_bootstrap.py

Extend the write-implement-env failure test to cover the fallback entry when `run-log append-failure` fails, and assert the fallback entry uses colon wording.

### UPDATED: skills/implement/scripts/test-write-final-report.sh

Update stale fixture assertions to match current renderer output:

- Happy-path title assertions use `## /implement run run-5: merged`.
- Design-only title assertion uses `## /implement run run-do: design-only`.
- Matrix title assertions look for `: $expected`.
- Top-reviewer assertion uses `cursor/correctness: 2`.

### UPDATED: skills/implement/scripts/write-final-report.md

Update the documented run-summary heading contract to `## /<skill> run <run-id>: <outcome>`.

### UPDATED: docs/run-logs.md

Update the final-summary heading contract to the colon format.

Leave unrelated examples that describe PR links or human prose outside this issue unchanged unless they are part of the same run-summary heading contract.

### UPDATED: skills/implement/SKILL.md

Update the Step 17 reference to the structured summary block so it shows `## /implement run ...: <outcome>`.

Do not add, remove, or convert Bash fences. No `scripts/test-implement-fence-shape.sh` change is needed.

### UPDATED: python/larch/report/final_report.py

Change both stalled-heading helpers and the predicate:

- Tighten `_summary_heading_line_is_stalled()` to require an H2 run-summary heading prefix before matching the stalled suffix. Only lines that start with `## /` (after stripping) and end with `: stalled` or `— stalled` are eligible. This prevents `- **Outcome**: stalled` bullets from matching.
- `summary_heading_is_stalled(text)` scans all lines and returns true on the first line that satisfies the tightened predicate.
- `_summary_stalled_heading_index(lines)` scans all lines and returns the index of the first line satisfying the tightened predicate.
- Keep compatibility with both legacy (`— stalled`) and current (`: stalled`) separators so old committed logs remain reconcilable.

### UPDATED: python/tests/report/test_run_logs.py

Add two cases:

- Positive: `final-summary.md` has non-heading content before the stalled H2; reconciliation finds and rewrites the stalled heading and outcome.
- Negative: `final-summary.md` has a `- **Outcome**: stalled` bullet but no stalled H2; helpers return false/None and reconciliation does not fire.

### UPDATED: python/tests/implement/test_ship.py

Add two cases for `_committed_summary_heading_is_stalled()`:

- Positive: committed final summary has prelude content before the stalled H2; returns true.
- Negative: only a `- **Outcome**: stalled` bullet with no stalled H2; returns false.

## Edge cases

- Preserve legacy stalled-heading support so old committed logs with the old separator remain repairable.
- Stalled detection must not match `- **Outcome**: stalled` bullets; require the H2 heading prefix.
- If multiple stalled headings exist, rewrite the first matching heading and the first stalled outcome bullet. This matches the current conservative behavior.
- Keep redaction truncation fail-closed. Only the marker punctuation changes.

## Failure modes

- A stale harness assertion can fail even when runtime output is correct.
- A broad stalled-heading scan could false-positive on non-heading prose if the predicate is loosened. The H2 prefix requirement prevents this.
- Changing timing-ledger labels would create wire-format churn. Do not touch them.
- Redaction marker changes can break exact-string tests. Update only tests that assert the real marker.

## Testing strategy

Run changed-file and targeted tests only:

- `python3 -m pytest python/tests/implement/test_ci_monitor.py -k collect_failed_logs`
- `python3 -m pytest python/tests/core/test_redact.py -k unterminated`
- `python3 -m pytest python/tests/state/test_bootstrap.py -k write_implement_env_failure`
- `python3 -m pytest python/tests/report/test_run_logs.py -k stalled_summary`
- `python3 -m pytest python/tests/implement/test_ship.py -k committed_summary_heading`
- `bash skills/implement/scripts/test-write-final-report.sh`

If Markdown changes trigger Mermaid lint, no Mermaid fences are expected in these edits.

## Acceptance

Run changed-file and targeted tests only:

- `python3 -m pytest python/tests/implement/test_ci_monitor.py -k collect_failed_logs`
- `python3 -m pytest python/tests/core/test_redact.py -k unterminated`
- `python3 -m pytest python/tests/state/test_bootstrap.py -k write_implement_env_failure`
- `python3 -m pytest python/tests/report/test_run_logs.py -k stalled_summary`
- `python3 -m pytest python/tests/implement/test_ship.py -k committed_summary_heading`
- `bash skills/implement/scripts/test-write-final-report.sh`

If Markdown changes trigger Mermaid lint, no Mermaid fences are expected in these edits.

mechanical_churn: false
diff_lines: 110

## Test plan
(no test plan section in plan-file)
