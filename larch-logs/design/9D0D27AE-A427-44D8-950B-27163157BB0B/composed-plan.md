## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Follow the round-1 scope decision: use Option 1 only.
- Do not change `issue parse-input`.
- Move Tier A marker insertion into the Tier A issue body composition path.
- Preserve Tier B behavior.

## Files to modify/create

### UPDATED: python/stall_recovery.py

- Change the `issue-input` branch in `compose_report`.
- Stop prepending `_report_marker(report_sig)` before `_compose_tier_a_issue(...)`.
- Pass the computed marker into `_compose_tier_a_issue(...)` as a new keyword, for example `dedup_marker=_report_marker(report_sig)`.
- In `_compose_tier_a_issue(...)`, place the marker directly after the `### {title}` line:
  - line 1: `### ...`
  - line 2: `<!-- larch-stall:signature=... -->`
  - then a blank line before `## Report metadata`.
- Keep the existing `marker: Path` parameter unchanged. It is the record-failure marker file, not the public dedup marker.
- Do not alter `_report_dedup_signature(...)`, `_report_marker(...)`, Tier B `chat-print`, redaction, or dedup lookup logic.

### UPDATED: python/test_stall_recovery.py

- Add a regression test near the existing report signature tests.
- Reuse `_compose_terminal_issue_input(...)` for the standard Tier A setup.
- Compose an `issue-input` report in dry-run mode.
- Capture `REPORT_DEDUP_SIGNATURE` from stdout.
- Read the generated issue input.
- Assert:
  - the first line starts with `### `;
  - the second line equals `<!-- larch-stall:signature=<captured-signature> -->`;
  - the marker does not appear before the title.
- Import and use `issue_create.parse_issue_input(...)`, or call `parse_input_main(...)`, to assert the parsed item body still contains the marker.
- Keep the test focused on marker preservation. Do not add network, GitHub, or filing behavior.

## Edge cases

- **Escalation-success reports** use the same `issue-input` branch, so the marker move should cover them without a separate code path.
- **Redaction** still runs after composition. The marker contains only a hash and should survive.
- **Tier B** already places the marker near the top of `chat-print`. Leave it unchanged.
- **Generic profile artifacts** still use the same Tier A branch when `--surface issue-input` is allowed.

## Failure modes

- If the marker remains before the heading, `parse_issue_input` will still drop it.
- If the marker is added both before and after the heading, dedup may work but the artifact will contain duplicate markers.
- If the new parameter name conflicts with the existing `marker: Path`, the code can confuse the public signature marker with the record-failure marker file.

## Testing strategy

- Run the focused regression:
  - `python3 -m pytest python/test_stall_recovery.py -k "dedup_signature or compose_report"`
- Run the issue parser tests if the regression imports or calls `issue_create`:
  - `python3 -m pytest python/test_issue_create.py`
- Run Python checks required for Python changes:
  - `make py-lint`
  - `make py-test`
- Run the repository lint required by AGENTS.md:
  - `make lint`

## Acceptance

- Run the focused regression:
  - `python3 -m pytest python/test_stall_recovery.py -k "dedup_signature or compose_report"`
- Run the issue parser tests if the regression imports or calls `issue_create`:
  - `python3 -m pytest python/test_issue_create.py`
- Run Python checks required for Python changes:
  - `make py-lint`
  - `make py-test`
- Run the repository lint required by AGENTS.md:
  - `make lint`

review_status: ok
rounds_completed: 2
diff_added: 35
diff_deleted: 2
mechanical_churn: false
diff_lines: 37
