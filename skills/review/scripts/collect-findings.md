# collect-findings.sh Contract

`skills/review/scripts/collect-findings.sh` waits for reviewer outputs, runs external output validation, scans dirty-tree sidecars, deduplicates findings, and writes the ballot file.

External outputs are collected with:

```bash
collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode
```

Description mode parses dual-list output using `### In-Scope Findings` and `### Out-of-Scope Observations`; missing one section is fail-open. Diff mode preserves single-list output by treating the entire output as in-scope findings.

Stdout is `KEY=value` only: `FINDINGS_COUNT`, `OOS_COUNT`, `DIRTY_DETECTED`, and `COLLECT_OK`.

Harness: `skills/review/scripts/test-collect-findings.sh`, wired through `make test-collect-findings`.
