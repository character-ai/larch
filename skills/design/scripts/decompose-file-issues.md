# decompose-file-issues.sh

**Purpose**: `prepare` (validate partition Markdown, emit `/larch:issue` batch input + intra-batch deps TSV, run cycle detection; drops prior batch artifacts at start and on non-`ok` status; cycle witness line in `prepare-python.log`), `annotate` (parse `/larch:issue` stdout into `partition-filed.md`; writes `.decompose-issues-filed` only when `ISSUES_FAILED=0`), and `close-original` (compose close comment, `redact-secrets.sh`, `gh issue comment --body-file`, `gh issue close`, `.decompose-original-closed` sentinel; uses `$DESIGN_TMPDIR/decompose/.decompose-close-comment-posted` so a retry after a successful comment but failed close does not duplicate the GitHub comment).

**Primary caller**: `/design` Split-path filing sequence in `skills/design/references/decompose-panel.md`.

**Security**: `close-original` always pipes the composed body through `scripts/redact-secrets.sh` before GitHub publication.

**Harness overrides**: `DECOMPOSE_REDACT_SH` substitutes the redactor; prepend a stub `gh` on `PATH` for offline `close-original` tests (`skills/design/scripts/test-decompose-file-issues.sh`); export the same `PATH` for every `close-original` invocation in the harness so the stub always wins over a system `gh`.
