# compose-review-findings.sh contract

`scripts/compose-review-findings.sh` converts plan-review and code-review
finding artifacts into `review-findings-full.md`. Code-review artifacts are
read from `$IMPLEMENT_TMPDIR/round-*/accepted-findings.md` and
`$IMPLEMENT_TMPDIR/round-*/rejected-findings.md`; the parent
`$IMPLEMENT_TMPDIR/rejected-findings.md` remains a fallback for older runs.

Inputs:

```text
--design-artifacts-dir DIR
--implement-tmpdir DIR
--issue N
--output PATH
```

The output is one markdown section per finding:

```markdown
### <id>: <reviewer> [<phase>/<outcome>]

<redacted finding body>
```

Missing inputs are treated
as "no findings"; the script still writes an empty markdown file and emits
`FINDINGS_TOTAL=0`.

The helper redacts tmpdir paths and token-shaped secrets before writing
sections, then HTML-escapes `<`, `>`, and bare `&` in every finding body so
that XML-like tag names cited in security findings (e.g.
`</reviewer_diff>`, `<scout_notes>`) are encoded as `&lt;…&gt;` and do not
trigger markdownlint/agent-lint XML-element warnings. Existing HTML entities
are preserved rather than double-encoded. The old inline/archive split was
removed when review findings moved from issue anchors to committed
`larch-logs/` files.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `scripts/test-compose-review-findings.sh`.
