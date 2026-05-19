# collect-findings.sh Contract

`skills/review/scripts/collect-findings.sh` waits for reviewer outputs, runs external output validation, scans dirty-tree sidecars, deduplicates findings, and writes the ballot file.

External outputs are collected with:

```bash
collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode
```

Collector stderr is captured to `$REVIEW_TMPDIR/collect-agent-results.log`; collector stdout is redirected directly to `$REVIEW_TMPDIR/collector-results.env` and unconditionally appended to the log for traceability. A non-zero collector exit is appended verbatim to `execution-issues.md` with `append-tool-failure.sh` before the helper exits. The log path resolver uses `LARCH_EXECUTION_ISSUES_LOG` when set; otherwise it falls back through `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`, `$IMPLEMENT_TMPDIR/execution-issues.md`, then `$REVIEW_TMPDIR/execution-issues.md`. For each structured collector result whose `STATUS` is not `OK`, the helper reads the result file, composes a failure capture containing the collector status, reviewer output file, and `${REVIEWER_FILE}.diag` sidecar content when present, then appends it under `External Reviewer Issues`.

Claude fallback waits are captured to `$REVIEW_TMPDIR/wait-for-claude-reviewers.log`; a non-zero wait exit is logged the same way before exiting.

Description mode parses dual-list output using `### In-Scope Findings` and `### Out-of-Scope Observations`; missing one section is fail-open. Diff mode preserves single-list output by treating the entire output as in-scope findings. The `parse_output` awk function normalizes multi-line finding bodies to a single space-joined line before writing the tab-delimited output, preventing `sort -u` from splitting continuation body lines into spurious empty-Reviewer/Concern findings. Any `##` heading that is not `### In-Scope Findings` or `### Out-of-Scope Observations` activates a skip state: subsequent lines are ignored until a recognized section header resets the state. This prevents commit-hash bullets from preamble sections (e.g. `## Commits since merge-base`) being promoted to findings. Entries whose `title` is empty (produced by narrative-only reviewer output with no list items) are silently dropped by `flush()` — they do not produce a "Reviewer finding" catchall row (#2254). Tab characters in `title` are replaced with a space in `flush()` to prevent TSV column corruption (#2265).

**Reviewer-column validation**: before writing a TSV row to `FINDINGS_FILE`, the `label` field (reviewer filename, e.g. `cursor-specialist-correctness-output.txt`) is validated against the pattern `*-output.txt`. Rows whose label does not match are skipped and a Warnings entry is appended to `execution-issues.md` via `append-execution-issue.sh`. This guards against column corruption from embedded tabs in finding titles that survived past the `flush()` tab-strip (e.g. from `parse_output_tsv` paths) — the primary fix is tab-stripping in `flush()`, and the label validation is defense-in-depth (#2265).

**No-findings sentinels**: `parse_output` short-circuits and emits zero findings when a reviewer file contains exactly the legacy literal `NO_ISSUES_FOUND` (checked via `grep -Fxq`) or, when `jq` is present, the JSON sentinel `{"no_issues_found": true}` (checked via `jq -e 'type == "object" and .no_issues_found == true'` on the first non-blank trimmed line). The JSON sentinel is the canonical form per #2156; the legacy literal remains accepted as a backward-compatible fallback.

**Inline-TSV protocol**: external reviewer outputs are probed with `parse_output_tsv` before the fail-open prose parser so inline structured rows are not collapsed into one generic diff-mode finding. Inline embedding is the primary TSV delivery path (not a fallback); sidecar file writes are an optional supplement when the session allows. Claude fallback outputs still prefer prose parsing first. `parse_output_tsv` invokes `validate-research-output.sh --structured-reviewer-mode --write-structured` on the same file to extract inline TSV records, then converts each record to the `title\tlabel\tbody` format used by the main findings loop. Normal inline TSV is collected silently — `collect-findings.sh` does not emit Step 3a tsv-fallback warnings when structured rows are present; malformed or missing inline TSV simply yields zero structured rows and the script may fall through to prose parsing without treating read-only-only delivery as an error. This parser is a no-op when no valid TSV header is found.

Stdout is `KEY=value` only: `FINDINGS_COUNT`, `OOS_COUNT`, `DIRTY_DETECTED`, `COLLECT_OK`, and `COLLECTOR_OUTPUT_FILE`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-collect-findings.sh`, wired through `make test-collect-findings`.
