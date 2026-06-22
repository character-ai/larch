## Decision 1: Repointing scope breadth
- **Question**: Repoint only the issue's evidence-listed duplicate sites, or sweep all duplicate KV/atomic-write/text-IO helpers repo-wide?
- **Resolution**: All duplicate sites repo-wide. Every duplicate `KEY=value` parser (`_parse_kv` / `_kv_parse` / `_parse_kv_text` / `_parse_kv_output` / `_parse_kv_lines` / `_parse_kv_stdout` family), every `_atomic_write` / `_write_text_atomic` copy, and every `_read_text` / `_write_text` / `_append_text` copy across `python/` is in scope for repointing and local-copy deletion.
- **Source**: user

## Decision 2: normalize_reviewer_label inclusion
- **Question**: Include `normalize_reviewer_label` in the new module, as the issue's proposed API lists?
- **Resolution**: Exclude from this PR. It is a single definition (`review_pipeline.py:1409`, one caller), not duplicated, and is reviewer-domain logic, not generic IO. The new module stays pure IO. This narrows the issue's literal API list.
- **Source**: user

## Decision 3: Module name and shape
- **Question**: `larch_io.py` vs `envfile.py`; one module or split?
- **Resolution**: One stdlib-only module `python/larch_io.py` holding the KV read/write, atomic-write, and text read/write/append helpers.
- **Source**: user

## Decision 4: Behavior-parity hard constraint
- **Question**: Must the unified helpers preserve each call-site's existing observable behavior?
- **Resolution**: Yes. "Behavior unchanged" is an issue acceptance gate. Divergent semantics must be preserved across the merge: KV file readers differ (`_kv_get_file` returns the FIRST match; `stall_recovery.read_kv` returns the LAST match and strips trailing `\r`), and `_atomic_write` copies differ in signature (`session_env` has `create_parent`/`mode`) and mechanism (`os.replace` vs `review_aggregate`'s `shutil.move`). The unified API must cover these via parameters/defaults so no call-site's behavior changes.
- **Source**: codebase

## Decision 5: Wire formats are untouchable
- **Question**: May on-disk wire formats change?
- **Resolution**: No. The `KEY=value` stdout grammar and `.sh` env-file on-disk format must not change. Refactor the parsing/writing helpers, not the formats. (Issue out-of-scope clause.)
- **Source**: codebase
