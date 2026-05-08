# scripts/refresh-anchor.sh — contract

`scripts/refresh-anchor.sh` is the single-call wrapper around the recurring two-script chain `scripts/assemble-anchor.sh` + `scripts/tracking-issue-write.sh upsert-anchor` that `/implement` uses at every anchor-section accumulation boundary. It exists so SKILL.md call sites that previously emitted two consecutive Bash blocks (one to assemble the body, one to upsert it) are a single Bash invocation, reducing visible step count and removing duplicated `mkdir -p anchor-sections` boilerplate.

## Inputs

- `--sections-dir DIR` (required) — directory containing one `<slug>.md` fragment per anchor section. The script `mkdir -p`s it before delegating to `assemble-anchor.sh`, covering fresh-session callers that have not yet written any fragment.
- `--issue N` (required) — tracking-issue number; forwarded to both helpers.
- `--anchor-id ID` (optional) — when set, pins the existing anchor for `upsert-anchor`. When omitted, `upsert-anchor` finds the existing anchor by its `<!-- larch:implement-anchor v1 issue=<N> -->` first-line marker, or creates a new comment if absent (Branch 2/3 seed-plant + Branch 4 fresh-creation paths).
- `--output PATH` (optional) — assembled-body path. Default: `$(dirname "$SECTIONS_DIR")/anchor-assembled.md` so a session tmpdir layout `$IMPLEMENT_TMPDIR/anchor-sections/` resolves to `$IMPLEMENT_TMPDIR/anchor-assembled.md` automatically.
- `--repo OWNER/REPO` (optional) — forwarded to `tracking-issue-write.sh`. When omitted, `upsert-anchor` resolves the repo via `gh repo view`.
- `--warnings-log PATH` (optional) — forwarded to `assemble-anchor.sh` so Mermaid sanitizer rejections and fail-closed tool errors are logged in the session execution-issues file.

When `--warnings-log` is omitted and `IMPLEMENT_TMPDIR` is set with a writable `$IMPLEMENT_TMPDIR/execution-issues.md`, the wrapper forwards that path automatically. Explicit `--warnings-log` wins over the environment default.

## Outputs

Stdout combines the envelopes of both delegates (in the order they ran):

```
ASSEMBLED=true
OUTPUT=<assembled-body-path>
ANCHOR_COMMENT_ID=<id>
ANCHOR_COMMENT_URL=<url>
UPDATED=true|false
```

On failure, the wrapper forwards the failing helper's `FAILED=true` / `ERROR=…` envelope verbatim:

- Exit 1 — assemble step failed (or invocation error). `assemble-anchor.sh` envelope reaches stdout.
- Exit 2 — upsert step failed (gh / repo error). Both helpers' envelopes reach stdout, in order.

The wrapper does not invent new envelope keys. Callers parse `ASSEMBLED=true` and `ANCHOR_COMMENT_ID=` exactly as they would have with the original two-call chain.

## Backwards compatibility

- `scripts/assemble-anchor.sh` and `scripts/tracking-issue-write.sh upsert-anchor` remain unchanged and continue to be callable directly. `rebase-rebump-subprocedure.md` step 6 historically called them in sequence; `/implement` SKILL.md updates use this wrapper at every anchor-section accumulation site listed in Step 0.5 "Anchor-section accumulation".
- Existing tests pinning the assemble-or-upsert contracts (`scripts/test-tracking-issue-write.sh`, the assemble-anchor's own implicit coverage) are unaffected — the wrapper only composes the two existing scripts.

## When to update

Update this file when the wrapper grows new flags, when the default `--output` path changes, warning-log derivation changes, or when failure-envelope semantics change. The wrapper itself is intentionally a thin composition; reviewer panels should resist suggestions to add behavior here that does not also belong on `assemble-anchor.sh` / `upsert-anchor`. Edit-in-sync rule: any change to the assemble/upsert KV envelopes must also propagate to `refresh-anchor.sh`'s output documentation and to SKILL.md's parsing rules.

## Test harness

`scripts/test-refresh-anchor.sh` covers happy-path composition (with `tracking-issue-write.sh` mocked via a stub on PATH), assemble-failure envelope forwarding, and upsert-failure envelope forwarding. The test stays sibling-located per `.claude/rules/script-md-siblings.md`.
