# collect-findings.sh Contract

`skills/review/scripts/collect-findings.sh` waits for reviewer outputs, runs external output validation, scans dirty-tree sidecars, deduplicates findings, and writes the ballot file.

External outputs are collected with:

```bash
collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode
```

Collector stderr/stdout is captured to `$REVIEW_TMPDIR/collect-agent-results.log`. A non-zero collector exit is appended verbatim to `execution-issues.md` with `append-tool-failure.sh` before the helper exits. The log path resolver uses `LARCH_EXECUTION_ISSUES_LOG` when set; otherwise it falls back through `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`, `$IMPLEMENT_TMPDIR/execution-issues.md`, then `$REVIEW_TMPDIR/execution-issues.md`. For each structured collector result whose `STATUS` is not `OK`, the helper composes a failure capture containing the collector status, reviewer output file, and `${REVIEWER_FILE}.diag` sidecar content when present, then appends it under `External Reviewer Issues`.

Claude fallback waits are captured to `$REVIEW_TMPDIR/wait-for-claude-reviewers.log`; a non-zero wait exit is logged the same way before exiting.

Description mode parses dual-list output using `### In-Scope Findings` and `### Out-of-Scope Observations`; missing one section is fail-open. Diff mode preserves single-list output by treating the entire output as in-scope findings.

Stdout is `KEY=value` only: `FINDINGS_COUNT`, `OOS_COUNT`, `DIRTY_DETECTED`, and `COLLECT_OK`.

Harness: `skills/review/scripts/test-collect-findings.sh`, wired through `make test-collect-findings`.
