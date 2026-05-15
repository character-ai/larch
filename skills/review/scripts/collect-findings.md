# collect-findings.sh Contract

`skills/review/scripts/collect-findings.sh` waits for reviewer outputs, runs external output validation, scans dirty-tree sidecars, deduplicates findings, and writes the ballot file.

External outputs are collected with:

```bash
collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode
```

Collector stderr is captured to `$REVIEW_TMPDIR/collect-agent-results.log`; collector stdout is redirected directly to `$REVIEW_TMPDIR/collector-results.env` and unconditionally appended to the log for traceability. A non-zero collector exit is appended verbatim to `execution-issues.md` with `append-tool-failure.sh` before the helper exits. The log path resolver uses `LARCH_EXECUTION_ISSUES_LOG` when set; otherwise it falls back through `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`, `$IMPLEMENT_TMPDIR/execution-issues.md`, then `$REVIEW_TMPDIR/execution-issues.md`. For each structured collector result whose `STATUS` is not `OK`, the helper reads the result file, composes a failure capture containing the collector status, reviewer output file, and `${REVIEWER_FILE}.diag` sidecar content when present, then appends it under `External Reviewer Issues`.

Claude fallback waits separate stdout (machine-parseable `DONE`/`TIMEOUT` records) and stderr (progress text): stdout goes to `$REVIEW_TMPDIR/wait-for-claude-reviewers-stdout.log`, stderr to `$REVIEW_TMPDIR/wait-for-claude-reviewers-stderr.log`. A non-zero wait exit is logged via `append_review_failure` and replayed to stderr, but does NOT abort collection — the script falls through to parse whatever stdout was produced. Each `TIMEOUT <idx> <name>` record in stdout is logged as a separate `External Reviewer Issues` failure entry via `append_review_failure`, and collection continues with the remaining successful slots (timed-out output files are absent or empty, so `parse_output` produces zero findings for them). This ensures a single stuck Claude reviewer slot cannot abort the entire collect step.

Description mode parses dual-list output using `### In-Scope Findings` and `### Out-of-Scope Observations`; missing one section is fail-open. Diff mode preserves single-list output by treating the entire output as in-scope findings.

**No-findings sentinels**: `parse_output` short-circuits and emits zero findings when a reviewer file contains exactly the legacy literal `NO_ISSUES_FOUND` (checked via `grep -Fxq`) or, when `jq` is present, the JSON sentinel `{"no_issues_found": true}` (checked via `jq -e 'type == "object" and .no_issues_found == true'` on the first non-blank trimmed line). The JSON sentinel is the canonical form per #2156; the legacy literal remains accepted as a backward-compatible fallback.

Stdout is `KEY=value` only: `FINDINGS_COUNT`, `OOS_COUNT`, `DIRTY_DETECTED`, `COLLECT_OK`, and `COLLECTOR_OUTPUT_FILE`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-collect-findings.sh`, wired through `make test-collect-findings`.
