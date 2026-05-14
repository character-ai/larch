# append-tool-failure.sh contract

## Purpose

Append a failing tool, helper, or agent invocation to an `/implement`
execution-issues log while preserving the captured stdout/stderr body
verbatim.

## Interface

```text
append-tool-failure.sh --log <path> --site <step-id> --tool <label> --exit-code <N> --category <category> --output-file <path> [--redact]
```

Supported categories are `Tool Failures`, `External Reviewer Issues`,
`CI Issues`, and `Warnings`.

The helper reads `--output-file` without truncation and wraps the exact
content in a markdown code fence under a bullet:

````markdown
- **Step <site> — <tool> failed (exit <N>)**:
  ```
  <captured content>
  ```
````

When `--redact` is present, the captured content is first passed through
`scripts/redact-secrets.sh`. The redaction pass preserves non-secret
content and replaces known token families before public surfaces consume
the log.

## Output

On success, stdout is the delegated `append-execution-issue.sh` envelope:

```text
APPENDED=true
LOG=<path>
```

Failures use `FAILED=true` / `ERROR=<message>` and exit non-zero. Callers
that must continue after a tool failure should invoke this helper
best-effort, usually with `|| true` after capturing its own command's
output.

## Invariants

- Bash 3.2 portable.
- No truncation of captured output.
- The write is delegated to `append-execution-issue.sh`, preserving its
  sibling-temp plus `mv` atomic insertion behavior.
- Missing input files fail before the log is modified.

## Harness

`scripts/test-append-tool-failure.sh` covers single-line, multi-line,
large-content, category routing, redaction, missing-input failure, and
delegate failure atomicity. It is intended to run directly and through
the relevant-checks script harness.

## Edit In Sync

When changing the entry format or category set, update
`scripts/append-execution-issue.md`, `skills/implement/SKILL.md`, and
callers that parse execution-issues markdown.
