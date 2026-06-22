### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch_io.py:57-63
- **Concern**: `atomic_write(..., exclusive=True)` must pre-unlink a fixed sibling temp before `O_CREAT|O_EXCL`. Scenario: `session_env._atomic_write` today unlinks `path.with_suffix(path.suffix + ".tmp")` before open; if `larch_io.atomic_write` skips that, a leftover `.tmp` makes the next session-env write fail with `FileExistsError` and breaks resume/retry paths covered by `test_session_env.py`
- **Proposed resolution**: Document and implement pre-unlink (and symlink refusal on the temp path) inside `atomic_write` when `exclusive=True` with a fixed `temp_name`/sibling `.tmp`; keep `session_env` repoint kwargs aligned with that contract

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:129-132
- **Concern**: `plan_review._write_atomic` repoint omits `create_parent=False`. Scenario: Current helper never calls `mkdir`; `larch_io.atomic_write` defaults `create_parent=True`, so a missing parent would silently succeed instead of failing, changing wire/env sidecar behavior on edge paths
- **Proposed resolution**: Repoint with `larch_io.atomic_write(..., create_parent=False, temp_name=f"{path.name}.tmp.{os.getpid()}")` (or equivalent pid-suffixed sibling temp) and add a focused parity test that parent is not auto-created

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch_io.py:57-65
- **Concern**: `atomic_write(..., exclusive=True)` contract omits pre-unlink of an existing sibling temp before `O_CREAT|O_EXCL`. Scenario: `session_env._atomic_write` unlinks `path.with_suffix(path.suffix + ".tmp")` before `O_EXCL` create; a shared helper that only `open(O_EXCL)` on a stale `.tmp` from a prior crash raises and blocks session-env / launcher writes
- **Proposed resolution**: Add to `### NEW: python/larch_io.py`: when `exclusive=True`, if `temp_name` (or the derived sibling `.tmp`) already exists, unlink it (with the same symlink guards) before `os.open(..., O_CREAT|O_EXCL)`; mirror current `session_env.py:377-378`

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/progress_report.py:1963-1969
- **Concern**: `progress_report._read_simple_env` is a third copy of simple KV-from-file parsing but is neither repointed nor listed as a deliberate grep exception. Scenario: Issue acceptance requires one definition per helper and a duplicate-helper grep with only documented exceptions; this helper will fail that gate
- **Proposed resolution**: Add `### MAY_UPDATE: python/progress_report.py` (or firm `### UPDATED:` if mechanical): replace `_read_simple_env` with `read_text(..., default="")` + `parse_kv` preserving best-effort `OSError` → `{}` via `on_error_default=True`, or explicitly add `progress_report._read_simple_env` to the post-refactor grep exception list with rationale

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/design_publish.py:22-27
- **Concern**: `design_publish._write_result_env` repoint omits empty-row wire semantics that `design_postplan` documents. Scenario: Current `"\n".join(...) + "\n"` writes a lone `\n` when `rows` is empty; `design_postplan` explicitly preserves empty-dict → empty file; repointing both through `format_kvs`/`write_kvs` without noting publish’s list input can change on-disk bytes for empty env files
- **Proposed resolution**: In `### UPDATED: python/design_publish.py`, state whether empty `rows` must stay a lone `\n` (wrapper writes `"\n"` explicitly) or become a zero-byte file like postplan; add a focused parity test if empty publish env is reachable

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agents.py:218-238
- **Concern**: python/agents.py IO duplicates left as MAY_UPDATE but omitted from acceptance grep exceptions. Scenario: Acceptance requires duplicate helper copies removed and Testing strategy ends with a duplicate-helper grep against expected exceptions; progress_report and dirty_tree are named deferrals but agents.py _read_text/_write/_append/_review_atomic_write_text are not, so the run can ship with four remaining text-IO clones while the stated acceptance criterion reads unmet or an operator over-expands scope into agents.py mid-refactor
- **Proposed resolution**: Add agents.py (_read_text, _write, _append, _review_atomic_write_text) to the Testing strategy expected-exceptions list with an explicit highest-ROI deferral note (None-path read semantics), or narrow the Acceptance bullet to cited modules only; do not firm-repoint agents.py unless parity is verified

### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/session_env.py:1673-1679
- **Concern**: Plan leaves a simple local KV parser outside larch_io. Scenario: The acceptance contract requires duplicate KV helpers to be removed, but _parse_text_kv would remain as another KEY=value parser after the proposed session_env repoints
- **Proposed resolution**: Replace the stale-plugin stdout parse with larch_io.parse_kv(..., skip_comments=True) or an equivalent shared-call wrapper, then delete _parse_text_kv

### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:227-257,2980-2987
- **Concern**: Plan does not preserve OSError fallback on best-effort design env readers. Scenario: The current readers return the default or {} when an existing env sidecar cannot be read; a direct read_text repoint can raise and abort design recovery or postplan paths
- **Proposed resolution**: Keep the local try/except OSError around larch_io.read_text for _read_env_value_last, _read_env_values, and _read_simple_env, or add a per-call on_error_default knob and use it only for these readers
