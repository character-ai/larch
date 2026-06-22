# Review Round 2

- Mode: `diff`
- 6 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_1: NDJSON structured parsing gate breaks legacy parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-exec-detail-parser-output.txt
- **Severity**: important
- **Concern**: Structured NDJSON parsing is entered when any row has a string `category` (`if structured_rows:`), not only when every non-empty line parses as a `dict`. That partial gate drops uncategorized dict bodies in the structured branch, mishandles interleaved malformed lines versus the old list-comprehension fallback, and can either lose exec bullets (mixed categorized warning + malformed line + uncategorized `### Tool Failures` body → Warnings (1), Exec Issues (0)) or inflate totals versus legacy `_refresh_issue_counts` when rows have null/missing/unknown `category` but markdown `body` content that the old per-row category filter skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require all non-empty lines to be dicts before structured parsing; otherwise concatenate every dict body (including rows without category) and run markdown or string-count fallback.
  - From dyn-dyn-exec-detail-parser-output.txt: Mirror the legacy gate: use the structured per-row path only when every non-empty NDJSON line parses as a `dict` (`all(isinstance(row, dict) for row in parsed if row is not None)`). For rows with non-string/missing/unknown `category`, either skip them (parity) or apply the same category filter before any markdown aggregation, and add a fixture asserting `null`/numeric `category` rows stay at `(0, 0)` unless explicitly intended.
  - From dyn-dyn-exec-detail-parser-output.txt: Gate structured parsing on `len(dict_rows) == len([x for x in parsed if x is not None])` (all parseable lines are dicts) before `if structured_rows:`; only use the partial-line tolerant path if that semantic change is explicitly desired, and document it in the plan/tests that lock legacy parity fixtures.


### FINDING_2: Dedupe keys derived from truncated/redacted display text collapse distinct rows
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `dedupe_key` is built from `display_text` after `MAX_DISPLAY_LEN` truncation and/or `redact_outbound`, not from the full normalized source text. Plain bullets, bold bullets, and secret-bearing warnings that differ only after the truncation window or before redaction can merge into one `×N` row while header totals still reflect separate events, so operators lose distinct entries in the detail list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Dedupe on normalized full first-line body (e.g. _dedupe_key_from_body); truncate/redact only for display_text.
  - From cursor-specialist-correctness-output.txt: Compute dedupe_key from normalized raw label+suffix before truncation; keep display_text truncated/redacted.
  - From cursor-specialist-edge-cases-output.txt: Dedupe on pre-redaction normalized key; keep redacted display_text for rendering only.
  - From codex-generic-output.txt: Build `dedupe_key` from normalized, untruncated row text, preferably redacted but not display-truncated, while keeping `display_text` bounded for rendering.


### FINDING_5: Enrich-phase OSError leaves final summary counts and detail diverged
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `_write_enriched_post_publish_summary` hits `OSError`, `invoke_render` may already have written run-summary counts while the Exec Issues and Warnings detail block is missing from `final-summary.md`. Failure-path warnings appended to `execution-issues.md` are not reflected because `load_result` is not reloaded, so published summary and counts omit them for that run; stderr/exit code are the only failure signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Re-load issue detail after failure-path append, or document that such warnings appear only on retry.
  - From cursor-specialist-edge-cases-output.txt: On enrich failure write a visible degraded marker into final-summary.md or use one atomic write so counts and detail cannot diverge.


### FINDING_6: `_is_example_fence` can skip real consecutive Bash fences
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_is_example_fence` drops any fence whose info, nearby prose, or first body comment contains “wrong”, “correct”, or “example”. A real adjacent Bash sequence like `# ensure correct branch` followed by another Bash fence is skipped entirely, so the lint can miss the consecutive-fence pattern it is meant to block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Remove the broad per-fence example filter, or restrict it to explicit WRONG/CORRECT pairs using the existing pair-level `_is_wrong_correct_pair` carve-out.


### FINDING_10: Missing test for empty execution-issues.md falling back to NDJSON
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test covers a zero-byte `execution-issues.md` with populated `execution-issues.ndjson`. An implement run could regress to `(0,0)` totals and an empty detail block without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a tmp_path fixture with touch()-empty markdown plus populated NDJSON; assert count_load_result and render_issue_detail_block match NDJSON rows.


### FINDING_11: Missing test for all-dict NDJSON without category keys but with section headings in body
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test covers NDJSON shaped as `[{"body":"### Tool Failures\n- a"},{"body":"### Warnings\n- b"}]`. Previously counted `(0,0)`; the new concat path should list rows, but the behavior change is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixture asserting count_load_result (1,1) and numbered rows via load_issue_detail_groups or _refresh_issue_counts.


