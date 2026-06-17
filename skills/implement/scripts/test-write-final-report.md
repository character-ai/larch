# test-write-final-report.sh

Offline harness covering final-summary file creation, tracking comment upsert,
required argument validation, implement outcome summary shape, token-data-missing
`--cost-unavailable`, corrupt all-zero token-report warning rendering, renderer
fallback behavior including degraded bucketed line counts, and stdout body
emission for the Step 17 `--print-stdout` callsite.

## Recent contract coverage

The harness verifies final-report wrapper integration still appends Review Phase
Detail for completed rounds. Reviewer timing appears as a plain fenced ASCII
chart when timing data exists, with raw labels, bare `Ns` durations, the
ledger-window `0:00-M:SS` title span, and no Mermaid timing directives. Final
reports do not pass `--no-gantt`.

Run with:

```bash
make test-write-final-report
```
