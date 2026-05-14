# compose-review-findings.sh contract

`scripts/compose-review-findings.sh` converts plan-review and code-review
finding artifacts into `review-findings-full.md`.

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
sections. The old inline/archive split was removed when review findings moved
from issue anchors to committed `larch-logs/` files.

Harness: `scripts/test-compose-review-findings.sh`.
