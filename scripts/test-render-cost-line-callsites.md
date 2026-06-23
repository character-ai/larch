# test-render-cost-line-callsites.sh

Callsite lint for final-summary top-chat contracts. It pins the `/implement`
Step 17/18 `write-final-report.sh --print-stdout` guards, the NEVER #20
verbatim full-body exception prose, and the `/design`
`render-final-summary --post-publish-only` full-body emit contract.

The common `/design` emit contract pins live in
`skills/shared/final-summary-emit.md`. The harness asserts the marker-first
profile extracts from in-context completed `<task-notification>` output, forbids
task-output re-reads and Bash/Python marker scraping, preserves the Read
fallback, and emits `REPORT_GATE_SIDECARS_FILE` sidecars after the summary body.

`skills/design/SKILL.md` keeps only site-specific gates and pointers. The
harness pins Step 0b cancel routes to the file-only profile, keeps the
post-publish gates in Step 5c/5d, and rejects reintroduced full marker-extraction
procedure prose in the design skill.

The `python3 python/cli.py token render-cost-line` allowlist remains deliberately
scoped to the deprecated standalone helper. This harness also negative-greps the
active SKILL.md files so cost-line-only orchestrator prose cannot be
reintroduced.
