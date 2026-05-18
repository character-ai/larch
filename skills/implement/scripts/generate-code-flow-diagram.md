# generate-code-flow-diagram.sh

Generates the Step 7a Mermaid code-flow diagram through a context-isolated
Claude subprocess, then validates the candidate with
`scripts/sanitize-mermaid-fragment.sh`. Emits `token-ledger.sh` and
`timing-ledger.sh` marks for "Step 7a — code flow diagram" on entry,
inheriting `LARCH_TIMING_LEDGER` and `LARCH_TOKEN_SESSION_ID` from the
caller environment.

Usage:

```bash
generate-code-flow-diagram.sh --implement-tmpdir PATH [--model claude-sonnet-4-6]
```

Output:

- `STATUS=ok|skipped|failed`
- `DIAGRAM_FILE=<path-or-empty>`
- `SKIP_REASON=<reason-or-empty>`

On success, the promoted file is `$IMPLEMENT_TMPDIR/code-flow-diagram.md`.
