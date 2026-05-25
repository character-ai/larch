# decompose-file-issues.sh

**Purpose**: `prepare` (validate partition Markdown, emit `/larch:issue` batch input + intra-batch deps TSV, run cycle detection), `annotate` (parse `/larch:issue` stdout into `partition-filed.md` + `.decompose-issues-filed` sentinel), and `close-original` (compose close comment, `redact-secrets.sh`, `gh issue comment --body-file`, `gh issue close`, `.decompose-original-closed` sentinel).

**Primary caller**: `/design` Split-path filing sequence in `skills/design/references/decompose-panel.md`.

**Security**: `close-original` always pipes the composed body through `scripts/redact-secrets.sh` before GitHub publication.

**Harness overrides**: `DECOMPOSE_REDACT_SH` substitutes the redactor; prepend a stub `gh` on `PATH` for offline `close-original` tests (`skills/design/scripts/test-decompose-file-issues.sh`).
