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
  [--allow-external-paths] \
  [--dry-run]
```

The file passed to `tracking-issue-summary.sh --content-file` is sections-only:
it must not contain the marker line. `tracking-issue-summary.sh` prepends the
marker itself.

Existing comments are located with a two-step fetch: list comments and match the
first line against the stable marker, then fetch the matching comment body by
ID so multiline markdown, tabs, and literal `\n` text round-trip.

`--repo`, when supplied, must match `OWNER/REPO`. When omitted, the helper
resolves it from `gh repo view` and validates that result before issuing any
`gh` call.

`--clear-architecture` and `--clear-code-flow` explicitly remove their
sections. An absent or empty `--*-file` means preserve any existing section, not
clear it. If both sections end up empty, the helper deletes the existing stable
comment or returns `UPSERT_STATUS=no-op` when no stable comment exists.

By default, `--architecture-file` and `--code-flow-file` must resolve under a
temporary root (`$TMPDIR`, `/tmp`, `/private/tmp`, `/var/folders`, or the larch
session cache under `~/.cache/larch/sessions`). `--allow-external-paths` is the
explicit override for non-temporary sources.

Only newly supplied `--*-file` inputs are revalidated with
`sanitize-mermaid-fragment.sh`. Preserved sections fetched from GitHub are
carried forward byte-for-byte instead of being re-sanitized on every upsert.

Existing comment parsing is heading-based with generic fence-depth tracking:
`## Architecture Diagram` and `## Code Flow Diagram` start sections even when
the following body is prose or the fence is separated by multiple blank lines,
while heading-looking text inside open fences is ignored. If the stored comment
ends with an unclosed fence, the helper fails closed instead of truncating the
preserved content.

Before dry-run preview or upsert, the composed sections-only body is passed
through `redact-secrets.sh` and `redact-tmpdir-paths.sh`; the delegated
`tracking-issue-summary.sh` call redacts again as defense in depth.

`--dry-run` prints two previews: the first includes the marker-prefixed comment
body that operators would publish, and the second (`--- content-file ---`)
prints the sections-only payload that is delegated to
`tracking-issue-summary.sh`.

Regression harness: `scripts/test-upsert-diagrams-comment.sh`. Makefile target:
`test-upsert-diagrams-comment`.
