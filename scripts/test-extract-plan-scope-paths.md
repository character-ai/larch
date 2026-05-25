# test-extract-plan-scope-paths.sh

Harness for `scripts/extract-plan-scope-paths.sh`.

It builds a fixture plan with a `## Files to modify/create` section, asserts newline output, asserts `-z` NUL-delimited output, and verifies the fallback path emitted when no scope headings are present.

Run:

```bash
bash scripts/test-extract-plan-scope-paths.sh
```

Primary script: `scripts/extract-plan-scope-paths.sh`.
