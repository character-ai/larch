# sanitize-mermaid-fragment.sh contract

## Purpose

Validate Mermaid fragments before they are written to public tracking-issue summaries, larch-log batches, or PR bodies. The sanitizer is intentionally narrow: it rejects the two Mermaid-breaking classes seen in issue #1404 and leaves all broader Mermaid syntax validation to `scripts/lint-mermaid-fences.sh` and Mermaid CLI.

See `skills/shared/mermaid-safe-content.md` for contributor-facing authoring guidance.

## Interface

```
sanitize-mermaid-fragment.sh --input <path>
sanitize-mermaid-fragment.sh --input <path> --from-md
sanitize-mermaid-fragment.sh
sanitize-mermaid-fragment.sh --input <path> --warnings-log <path> --warnings-step <step>
```

Default mode treats the input as raw fence interior. `--from-md`, or an input whose first non-blank line is exactly ```` ```mermaid ````, treats the file as Markdown and extracts each top-level Mermaid fence as an independent validation unit. Nested documentation fences are ignored using the same fenced-block state-machine model documented in `lint-mermaid-fences.sh`.

## Policy

- Flowchart / graph diagrams reject literal `|` inside node text delimited by `[...]`, `(...)`, `{...}`, or `((...))`.
- Flowchart edge labels such as `A -->|label| B` are allowed because they are outside node brackets.
- Quoted node text such as `A["foo|bar"]` is allowed, including escaped quotes.
- `sequenceDiagram` participant and actor aliases reject `<br/>`, `<br />`, `<br>` case-insensitively and reject `$`.
- Other diagram types are not checked by this sanitizer.

The flowchart scanner uses explicit outside-bracket, inside-bracket-unquoted, and inside-bracket-quoted states. `\"` inside quoted node text does not end the quote.

## Output

Stdout is machine-readable only:

```
STATUS=ok
FENCE_COUNT=<N>
FENCE_1_HEADING=<architecture|code-flow|unknown>
```

or:

```
STATUS=rejected
REASON_TOKEN=<short-token> fence=<N> line=<N>
FENCE_COUNT=<N>
FENCE_1_HEADING=<architecture|code-flow|unknown>
```

Heading keys are emitted in Markdown mode and are inferred from a preceding `## Architecture Diagram` or `## Code Flow Diagram` heading within the last five non-blank lines.

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Accepted |
| 1 | Rejected by policy |
| 2 | Internal error |

Callers that publish content must treat exit 2 as fail-closed and omit the affected Mermaid fence.

## Warnings Log

When `--warnings-log` is supplied, rejection or internal error appends a public-safe `### Warnings` entry via `scripts/append-execution-issue.sh`:

```
- **Step <N> — mermaid sanitizer rejected:** <REASON_TOKEN(s)>
```

Raw source excerpts are never written to stdout or the warnings log.

## Test Harness

`scripts/test-mermaid-fragments.sh` covers the pinned reject/accept cases, mixed-fence Markdown mode, output token shape, warnings-log append behavior, and `lint-mermaid-fences.sh` nested-fence handling.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
