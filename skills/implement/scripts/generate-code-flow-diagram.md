# generate-code-flow-diagram.sh

Generates the Step 7a Mermaid code-flow diagram through a context-isolated
Claude subprocess, then validates the candidate with
`scripts/sanitize-mermaid-fragment.sh`. Emits `token-ledger.sh` and
`timing-ledger.sh` marks for "Step 7a — code flow diagram" on entry,
inheriting `LARCH_TIMING_LEDGER` and `LARCH_TOKEN_SESSION_ID` from the
caller environment.

Usage:

```bash
generate-code-flow-diagram.sh --implement-tmpdir PATH [--model claude-sonnet-4-6] [--base-remote NAME] [--base-ref BRANCH]
```

The default base target is `origin/main`. `step-7a.sh` passes `upstream/main`
when its `forked_target` is true, set via `--forked-target` argv or
`LARCH_FORKED_TARGET` in `session-env.sh`, not via direct shell environment.
`--base-remote` and `--base-ref` values must match `^[A-Za-z0-9._/-]+$`.

Output:

- `STATUS=ok|skipped|failed`
- `DIAGRAM_FILE=<path-or-empty>`
- `SKIP_REASON=<reason-or-empty>`

On success, the promoted file is `$IMPLEMENT_TMPDIR/code-flow-diagram.md`.
