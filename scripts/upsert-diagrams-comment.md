# upsert-diagrams-comment.sh contract

`scripts/upsert-diagrams-comment.sh` is the shared owner for the
issue-scoped `<!-- larch:diagrams v1 -->` tracking comment. `/design` Step 5c.5
writes the Architecture section; `/implement` Step 7a writes the Code Flow
section. The helper preserves the section it was not asked to replace.

Synopsis:

```bash
scripts/upsert-diagrams-comment.sh --issue N \
  [--repo OWNER/REPO] \
  [--architecture-file PATH | --clear-architecture] \
  [--code-flow-file PATH | --clear-code-flow] \
  [--marker '<!-- larch:diagrams v1 -->'] \
  [--dry-run]
```

The file passed to `tracking-issue-summary.sh --content-file` is sections-only:
it must not contain the marker line. `tracking-issue-summary.sh` prepends the
marker itself.

Existing comments are located with a two-step fetch: list comments and match the
first line against the stable marker, then fetch the matching comment body by
ID so multiline markdown, tabs, and literal `\n` text round-trip.

`--clear-architecture` and `--clear-code-flow` explicitly remove their
sections. An absent or empty `--*-file` means preserve any existing section, not
clear it.

Before dry-run preview or upsert, the composed sections-only body is passed
through `redact-secrets.sh` and `redact-tmpdir-paths.sh`; the delegated
`tracking-issue-summary.sh` call redacts again as defense in depth.

Regression harness: `scripts/test-upsert-diagrams-comment.sh`. Makefile target:
`test-upsert-diagrams-comment`.
