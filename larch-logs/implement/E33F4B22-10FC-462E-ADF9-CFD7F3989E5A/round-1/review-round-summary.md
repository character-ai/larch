# Review Round 1

- Mode: `diff`
- 7 accepted, 6 rejected (3 neutral)

## Accepted Findings

### FINDING_4: malformed NDJSON line drops otherwise valid structured rows
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When any NDJSON line is malformed, valid structured exec-issue or warning rows are lost. A warning dict plus one bad line can yield `Warnings (0)` because fallback loses category metadata and only string-counts the body. Mixed valid/invalid lines can report zero warnings and omit the detail section.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Parse valid dict rows by category while ignoring malformed rows, or synthesize category headings before markdown fallback.
  - From codex-specialist-edge-cases-output.txt: Parse valid category-bearing dict rows structurally even when other lines are malformed


### FINDING_5: markdown-table vote recovery discards axis tokens
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `python/voting.py` table-row recovery drops `CORRECTNESS`, `SEVERITY`, `QUALITY`, and `UNCERTAIN` axis tokens. A row like `YES` plus `CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false` parses as `YES` with blank axes and `uncertain=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Preserve axis assignment cells before the optional -- reason suffix when rewriting table rows.


### FINDING_7: silent `OSError` swallow after exec/warning detail append in `design_summary.py`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-summary-splice-output.txt
- **Severity**: important
- **Concern**: Post-phase `except OSError: pass` after in-memory detail splice lets tracking upsert publish a summary missing the required `## Exec Issues and Warnings` block. If `write_text` fails after `_append_issue_detail` builds the full body, upsert may upload the older `invoke_render` file with count bullets but no detail section, diverging from stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fail closed on OSError (log + non-zero return) or atomic write-before-upsert; skip upsert when the enriched body was not durably written.
  - From dyn-dyn-summary-splice-output.txt: On `OSError`, log to `execution-issues.md`, return non-zero before upsert, or upsert from the in-memory `body` via a temp file rather than the possibly stale on-disk file.


### FINDING_8: truncating exec issue display text before redaction can leak partial secrets
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Long warning text with a secret crossing `MAX_DISPLAY_LEN` can render a partial token prefix (e.g. `sk-`) before redaction runs. That fragment can reach render and assessment prompt paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Redact raw display strings before truncation and reuse the redacted text for render and prompt paths
  - From codex-specialist-testing-output.txt: Redact raw bullet text before truncation and add a boundary regression test


### FINDING_11: missing fail-closed tests for assessment subprocess timeout and non-zero exit
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required fail-closed paths for assessment subprocess `TimeoutExpired` and non-zero exit are untested. A change that stops catching those cases could cause final-summary rendering to fail or hang instead of degrading to rows without assessments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Mock subprocess.run to raise TimeoutExpired and to return returncode=1; assert assess_issue_details returns {} and render_issue_detail_block still emits rows without assessment lines.


### FINDING_14: `_fallback_event` dedupe uses truncated display_text
- **Reviewer(s)**: dyn-dyn-exec-detail-parser-output.txt
- **Severity**: important
- **Concern**: `_fallback_event` uses the same truncated `display_text` for rendering and `dedupe_key`. NDJSON rows whose `body` has no parseable bullets but multiple non-empty lines keep only the first line for display; rows sharing a first line but differing later can collapse incorrectly. Legacy counting did not dedupe, so this is a new listing regression on the structured NDJSON path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-exec-detail-parser-output.txt: for fallback rows, key dedupe on a normalized full first-paragraph / full `body.strip()` (with a sane max length cap separate from display truncation), or skip dedupe for fallback-derived events.


### FINDING_17: degraded `design_summary` fallback can show detail section without matching count bullets
- **Reviewer(s)**: dyn-dyn-summary-splice-output.txt
- **Severity**: important
- **Concern**: When `invoke_render` fails, the degraded fallback writes a summary without `- **Exec issues**` / `- **Warnings**` bullets, but the post phase still splices `## Exec Issues and Warnings` from the earlier `load_result`. The document can show missing top-level count bullets alongside a detailed section with non-zero headers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-summary-splice-output.txt: In the degraded fallback branch, emit exec/warning bullets from the already-computed `exec_issues` / `warnings`, or skip detail append when the renderer failed and only a minimal fallback was written.


