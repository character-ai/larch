### FINDING_1: atomic_write(exclusive=True) must pre-unlink sibling temp before O_CREAT|O_EXCL
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `larch_io.atomic_write(..., exclusive=True)` must unlink an existing fixed sibling temp (e.g. `.tmp`) before `os.open(..., O_CREAT|O_EXCL)`. `session_env._atomic_write` already does this; without parity, a stale `.tmp` from a prior crash or interrupted write raises `FileExistsError` and breaks session-env / launcher resume and retry paths covered by `test_session_env.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document and implement pre-unlink (and symlink refusal on the temp path) inside `atomic_write` when `exclusive=True` with a fixed `temp_name`/sibling `.tmp`; keep `session_env` repoint kwargs aligned with that contract
  - From Cursor-Pragmatic: Add to `### NEW: python/larch_io.py`: when `exclusive=True`, if `temp_name` (or the derived sibling `.tmp`) already exists, unlink it (with the same symlink guards) before `os.open(..., O_CREAT|O_EXCL)`; mirror current `session_env.py:377-378`

### FINDING_2: plan_review._write_atomic repoint omits create_parent=False
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `plan_review._write_atomic` repoint omits `create_parent=False`. The current helper never calls `mkdir`; `larch_io.atomic_write` defaults `create_parent=True`, so a missing parent would silently succeed instead of failing, changing wire/env sidecar behavior on edge paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Repoint with `larch_io.atomic_write(..., create_parent=False, temp_name=f"{path.name}.tmp.{os.getpid()}")` (or equivalent pid-suffixed sibling temp) and add a focused parity test that parent is not auto-created

### FINDING_3: progress_report._read_simple_env duplicate not repointed or excepted
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `progress_report._read_simple_env` is a third copy of simple KV-from-file parsing but is neither repointed nor listed as a deliberate grep exception. Acceptance requires one definition per helper and a duplicate-helper grep with only documented exceptions; this helper will fail that gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `### MAY_UPDATE: python/progress_report.py` (or firm `### UPDATED:` if mechanical): replace `_read_simple_env` with `read_text(..., default="")` + `parse_kv` preserving best-effort `OSError` → `{}` via `on_error_default=True`, or explicitly add `progress_report._read_simple_env` to the post-refactor grep exception list with rationale

### FINDING_4: design_publish._write_result_env empty-row wire semantics unspecified
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `design_publish._write_result_env` repoint omits empty-row wire semantics that `design_postplan` documents. Current `"\n".join(...) + "\n"` writes a lone `\n` when `rows` is empty; `design_postplan` explicitly preserves empty-dict → empty file. Repointing both through `format_kvs`/`write_kvs` without noting publish’s list input can change on-disk bytes for empty env files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `### UPDATED: python/design_publish.py`, state whether empty `rows` must stay a lone `\n` (wrapper writes `"\n"` explicitly) or become a zero-byte file like postplan; add a focused parity test if empty publish env is reachable

### FINDING_5: agents.py IO duplicates omitted from acceptance grep exceptions
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `python/agents.py` IO duplicates left as `MAY_UPDATE` but omitted from acceptance grep exceptions. Acceptance requires duplicate helper copies removed and Testing strategy ends with a duplicate-helper grep against expected exceptions; `progress_report` and `dirty_tree` are named deferrals but `agents.py` `_read_text`/`_write`/`_append`/`_review_atomic_write_text` are not, so the run can ship with four remaining text-IO clones while the stated acceptance criterion reads unmet or an operator over-expands scope into `agents.py` mid-refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add agents.py (`_read_text`, `_write`, `_append`, `_review_atomic_write_text`) to the Testing strategy expected-exceptions list with an explicit highest-ROI deferral note (None-path read semantics), or narrow the Acceptance bullet to cited modules only; do not firm-repoint agents.py unless parity is verified

### FINDING_6: session_env._parse_text_kv left outside shared larch_io KV surface
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Plan leaves a simple local KV parser (`_parse_text_kv`) outside `larch_io`. The acceptance contract requires duplicate KV helpers to be removed, but `_parse_text_kv` would remain as another `KEY=value` parser after the proposed `session_env` repoints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Replace the stale-plugin stdout parse with `larch_io.parse_kv(..., skip_comments=True)` or an equivalent shared-call wrapper, then delete `_parse_text_kv`

### FINDING_7: design_lifecycle env readers may lose OSError fallback on repoint
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Plan does not preserve `OSError` fallback on best-effort design env readers. Current readers return the default or `{}` when an existing env sidecar cannot be read; a direct `read_text` repoint can raise and abort design recovery or postplan paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Keep the local try/except OSError around `larch_io.read_text` for `_read_env_value_last`, `_read_env_values`, and `_read_simple_env`, or add a per-call `on_error_default` knob and use it only for these readers
```
