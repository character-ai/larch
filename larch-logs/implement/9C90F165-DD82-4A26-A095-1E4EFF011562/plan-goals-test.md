## Goal
Implement issue #4975: [IMPLEMENTING] [py-code-quality] Add shared larch_io util for KV/atomic-write/text-IO helpers.

## Implementation Plan
## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Use direct code inspection as the plan source.
- Keep the approved outline binding:
  - Add one `python/larch_io.py`.
  - Repoint duplicate IO helpers across `python/`.
  - Do not move `normalize_reviewer_label`.
  - Do not change `KEY=value` or `.sh` env-file wire formats.
- Implement a parameterized shared API instead of changing call-site behavior:
  - `parse_kv(text, *, first_wins=False, skip_empty_key=False, cr_strip="none", strip_value=False, key_pattern=None, allowed_keys=None, skip_comments=False)`
  - `kv_value(text, key, *, default="", first_match=True, cr_strip="none")`
  - `read_kv(path, key, *, default="", first_match=True, cr_strip="none", errors="replace", on_error_default=False, empty_value_means_default=False, reject_symlink=False)`
  - `read_kvs(path, *, default=None, first_wins=False, cr_strip="none", skip_comments=False, key_pattern=None, errors="replace", reject_cr=False, reject_symlink=False, on_error_default=False)`
  - `format_kvs(values, *, sort_keys=False)` — accepts `Mapping[str, object]` **or** `Iterable[tuple[str, object]]`; preserves input order (no sort unless `sort_keys=True`).
  - `write_kvs(path, values, *, sort_keys=False, atomic=True, create_parent=True, mode=None)` — **raises `OSError` on write failure**; bool-return swallow lives only in local wrappers.
  - `read_text(path, *, default=None, errors="replace")`
  - `write_text(path, text, *, create_parent=True)`
  - `append_text(path, text, *, create_parent=True)`
  - `atomic_write(path, text, *, create_parent=True, mode=None, prefix=None, suffix=".tmp", temp_name=None, replace_method="replace", nofollow=False, exclusive=False, newline=None)`
- `cr_strip` accepts only `"none"`, `"suffix"` (`removesuffix("\r")`), `"rstrip"` (`rstrip("\r")`), or `"strip"` (`strip("\r")`). Default `"none"`. Map each repoint explicitly; do not homogenize divergent CR handling behind a single boolean.
- Default `skip_empty_key=False` so bare `parse_kv` repoints preserve empty-key lines (`=value` under key `""`). Call sites that currently reject empty keys pass `skip_empty_key=True` explicitly.
- Default `on_error_default=False` on `read_kv` / `read_kvs` so I/O failures propagate unless a call site opts into best-effort empty/default fallback.
- **No `errors` parameter on `parse_kv`** — text is already decoded; callers that need `errors="replace"` decode at `read_text` / `read_kvs` / `read_kv` and pass the resulting string to `parse_kv`.
- Keep signatures small, but include the knobs needed for known divergences:
  - first match vs last match.
  - first-wins dict parse vs last-wins dict parse.
  - per-site `cr_strip` mode (`none` / `suffix` / `rstrip` / `strip`).
  - value `.strip()` variants.
  - key allowlists and key regex validation.
  - `empty_value_means_default` for `KEY=` → default semantics.
  - read-side `reject_symlink` for env files that must not follow symlinks.
  - read-side `reject_cr=True` on `read_kvs` / `read_text` for callers that need whole-file CR rejection (not used for session-env primary loader; see `session_env` section).
  - symlink-safe `session_env` writes via `nofollow=True` plus `exclusive=True` (`O_CREAT|O_EXCL`) temp creation, with **pre-unlink of an existing fixed sibling temp** before `os.open`.
  - `shutil.move` behavior where it is currently used.
  - non-atomic `write_kvs(..., atomic=False)` with local bool-return wrappers that catch `OSError` and return `False`.
- Repoint each module by importing `larch_io`.
- Delete local duplicate helper definitions after all local callers move.
- Remove imports that become unused.
- Keep wrappers only when they preserve a public API or encode call-site-specific semantics that are clearer local than as shared defaults.

## Files to modify/create

### NEW: python/larch_io.py

- Add the shared stdlib-only helper module.
- Add docstrings that state wire-format preservation and document each knob's purpose.
- Use only stdlib imports.
- Prefer deterministic small helpers over a class.
- `parse_kv`: default `skip_empty_key=False`; document when callers should pass `skip_empty_key=True`. Operates on already-decoded `str`; no `errors` kwarg. Implement `cr_strip` with exact semantics: `"suffix"` → `removesuffix("\r")`, `"rstrip"` → `rstrip("\r")`, `"strip"` → `strip("\r")`, `"none"` → no mutation.
- `read_kv` / `read_kvs`: support `empty_value_means_default`, `reject_symlink`, `errors`, `reject_cr`, `on_error_default`, and per-site `cr_strip`.
- `read_kvs`: return `default` (or `{}`) when path is missing, not a file, or `reject_symlink=True` and path is a symlink; when `reject_cr=True`, raise `ValueError` if `\r` appears anywhere in decoded file body.
- `format_kvs`: accept `Mapping[str, object]` or `Iterable[tuple[str, object]]`; emit `KEY=value\n` rows in input order unless `sort_keys=True`.
- `write_kvs`: raise `OSError` on failure; do not swallow errors or return bool.
- Support text atomic writes with:
  - parent creation control.
  - optional file mode and `fchmod` after `O_EXCL` create.
  - optional symlink refusal on path and temp (`nofollow=True`).
  - `exclusive=True` using `O_CREAT|O_EXCL` (and `O_NOFOLLOW` when available) for session-env hardening.
  - **when `exclusive=True` and a fixed `temp_name` (or derived sibling `.tmp`) is used**: if that temp path already exists, refuse symlinked temps, then unlink the existing temp (with `contextlib.suppress(FileNotFoundError)`) **before** `os.open(..., O_CREAT|O_EXCL)` so stale crash leftovers do not raise `FileExistsError`; mirror current `session_env._atomic_write` lines 377-378.
  - configurable temp naming (`prefix`, `suffix`, `temp_name`).
  - `os.replace` by default.
  - `shutil.move` when `replace_method="move"`.
  - optional `newline="\n"` for mkstemp-style writers.
- Reuse `contextlib.suppress`; do not recreate a suppress class.

### NEW: python/test_larch_io.py

- Add focused parity tests for:
  - default last-wins KV parsing.
  - first-wins parsing.
  - empty-key retention (`skip_empty_key=False` default).
  - empty-key rejection when `skip_empty_key=True`.
  - comment skipping.
  - `cr_strip` modes: `none`, `suffix`, `rstrip`, `strip` (including values with interior `\r` where modes diverge).
  - value `.strip()` behavior.
  - `read_kv` first-match and last-match modes.
  - `empty_value_means_default` (`KEY=` → default).
  - `reject_symlink` on `read_kvs` / `read_kv`.
  - `reject_cr=True` raising on CRLF file bodies.
  - missing-file defaults.
  - strict UTF-8 decode failure with `errors="strict", on_error_default=True` returning empty/default.
  - `on_error_default=False` propagating `OSError` / decode errors.
  - `format_kvs` ordering for both dict and iterable tuple inputs.
  - `write_kvs` preserving insertion order by default.
  - `write_kvs(..., atomic=False)` raising `OSError` on failure (not bool-return).
  - `atomic_write` parent creation.
  - `atomic_write` mode setting when requested.
  - `atomic_write` `exclusive=True` + `nofollow=True` symlink refusal.
  - `atomic_write` `exclusive=True` with fixed sibling `temp_name`: pre-unlink of an existing stale temp before `O_EXCL` create succeeds.
  - `read_text`, `write_text`, and `append_text` behavior.

### UPDATED: python/bootstrap.py

- Replace `_parse_kv` with `larch_io.parse_kv(..., skip_comments=True, cr_strip="rstrip")`.
- Replace `_atomic_text` with `larch_io.atomic_write` using sibling temp name `path.name + f".tmp.{pid}"` via `temp_name` or equivalent.
- Replace `_read_simple_kv` with `larch_io.read_kv(..., first_match=True, cr_strip="suffix", reject_symlink=True, on_error_default=True)`.
- Replace `_parse_env_lines` with `larch_io.parse_kv(text, allowed_keys=ROUTING_KEYS, key_pattern=_KEY_RE.pattern)` (or equivalent frozen allowlist/regex) and delete the local helper.
- Keep shell-assignment parsing code local if it uses `shlex` or route-specific allowlists beyond generic KV parsing.
- Update private test references if `_parse_kv` is removed.

### UPDATED: python/admission.py

- Replace `_atomic_text` with `larch_io.atomic_write` using mkstemp-style `prefix=f".{path.name}."`, `newline="\n"`, parent creation, and `os.replace` semantics.
- Preserve current cleanup-on-failure temp unlink behavior.

### UPDATED: python/tokens.py

- Replace `_atomic_text` with `larch_io.atomic_write` using mkstemp-style `prefix=f".{path.name}."`, `newline="\n"`, and parent creation.
- Refactor `token_claude_source` snapshot read: `text = larch_io.read_text(snap, errors="replace")` then `larch_io.parse_kv(text, allowed_keys={"TRANSCRIPT_PATH", "SESSION_DIR", "SESSION_UUID"})` with local post-check for required keys; keep replay validation logic local.
- Repoint `parse_token_record_sidecar` sidecar loop via `read_text(..., errors="replace")` + `larch_io.parse_kv` (last-wins default).
- Repoint `_raw_tool_from_sidecar` via `read_text(..., errors="replace")` + `larch_io.kv_value(..., key="TOOL", default="")` (first-match).
- Repoint lane sidecar reads in `TokenLaneReporter.report` via `read_text(..., errors="replace")` + `larch_io.parse_kv` (last-wins default).
- Repoint any other cited allowlisted KV loops through `read_text` + `larch_io.parse_kv` / `kv_value` with matching first/last-match and `allowed_keys` semantics.

### UPDATED: python/plan_review.py

- Replace `_parse_kv_text` with `larch_io.parse_kv`.
- Replace `_read_kv_file` with a thin wrapper or `larch_io.read_kvs(..., reject_symlink=True, default={})` so symlink paths return `{}` without following the target.
- Replace `_write_atomic` with `larch_io.atomic_write(..., create_parent=False, temp_name=f"{path.name}.tmp.{os.getpid()}")` (or equivalent pid-suffixed sibling temp) so missing parent directories still fail instead of being auto-created.
- Preserve missing-file and symlink-refusal behavior.

### UPDATED: python/review_tally.py

- Replace `_kv_parse` with `larch_io.parse_kv`.
- Replace `_read` with `larch_io.read_text`.
- Replace `_write` with `larch_io.write_text`.
- Replace `_append` with `larch_io.append_text`.
- Preserve last-wins behavior and current handling of empty keys.

### UPDATED: python/design_lifecycle.py

- Replace `_write_text` with `larch_io.write_text`.
- Replace `_read_env_value` with `larch_io.read_kv(..., first_match=True, empty_value_means_default=True, reject_symlink=True, on_error_default=True, errors="replace")`.
- Keep `_read_env_value_last` as a **local line-iterating wrapper** over `larch_io.read_text(..., errors="replace")` wrapped in `try`/`except OSError` returning `default` on read failure; scan prefix matches and update the result only when each candidate is non-empty (preserve last-nonempty semantics: `FOO=ok` then `FOO=` still returns `ok`); do not route through dict-based `read_kv`/`read_kvs`.
- Keep `_read_env_values` as a **local line-iterating wrapper** over `larch_io.read_text(..., errors="replace")` wrapped in `try`/`except OSError` returning `out` on read failure; merge into defaults and update a key only when the parsed value is non-empty; do not route through dict-based `read_kvs`.
- Replace `_read_simple_env` with symlink refusal (`path.is_symlink()` → `{}`) and missing/non-file → `{}` before read, then `try`/`except OSError` around `larch_io.read_text(..., errors="replace")` returning `{}` on failure, then `larch_io.parse_kv(text, allowed_keys=allow)` (last-wins default), then **locally filter** to drop entries where `"\n" in value` or `"\r" in value`.
- Replace `_write_kv_file` with a bool-return wrapper around `larch_io.write_kvs(..., atomic=False, create_parent=False)` that catches `OSError` and returns `False` on failure, `True` on success; do not use atomic write here.
- Leave shell-decoding env readers local where `shlex` / route-specific parsing cannot be preserved by generic KV helpers.
- Preserve parent creation for all current `_write_text` writes.

### UPDATED: python/phantom.py

- Replace `_parse_kv_output` with `larch_io.parse_kv`.
- Preserve `partition("=")` behavior for lines with `=`.

### UPDATED: python/ci_agentic_fix.py

- Replace `_parse_kv` with `larch_io.parse_kv(..., strip_value=True, skip_empty_key=True)`.
- Preserve the current requirement that keys are non-empty.

### UPDATED: python/design_publish.py

- Replace `_parse_kv` with `larch_io.parse_kv`.
- Replace `_write_result_env` with a bool-return wrapper over `larch_io.write_kvs(..., atomic=False, create_parent=False)` that catches `OSError` and returns `False` on failure (same pattern as `design_lifecycle._write_kv_file`).
- Preserve last-wins behavior.

### UPDATED: python/review_pipeline.py

- Replace `_kv_parse` with `larch_io.parse_kv(..., skip_empty_key=True)`.
- Replace `_kv_get_file` with `larch_io.read_kv(..., first_match=True, default="")` or equivalent preserving first-match prefix scan.
- Replace `_write_text`, `_append_text`, and `_atomic_write` with shared helpers.
- Delete the local `contextlib_suppress` class.
- Import `contextlib.suppress` or rely on `larch_io.atomic_write` cleanup.
- Preserve parent creation before writes.

### UPDATED: python/rendering.py

- Replace `_read_text` with `larch_io.read_text`.
- Replace `_write_text_atomic` with `larch_io.atomic_write`.
- Preserve current exception behavior for missing reads.
- Preserve temp prefix and suffix if tests or callers observe it.

### UPDATED: python/research.py

- Replace `_write_text_atomic` with `larch_io.atomic_write` using sibling temp `temp_name=f".{path.name}.{os.getpid()}.tmp"` (or equivalent) and `create_parent=True`.
- Preserve sibling temp naming.

### UPDATED: python/decompose.py

- Replace `_parse_kv_lines` with `larch_io.parse_kv`.
- Keep `_read_text_or_empty` local only if its “missing means empty” behavior is clearer than using `read_text(default="")`.

### UPDATED: python/oos_filer.py

- Replace `_parse_kv` with `larch_io.parse_kv(..., cr_strip="strip")`.
- Replace `_read_kv_file` with `larch_io.read_kvs(..., cr_strip="strip")`.
- Preserve trailing `\r` stripping for both stdout/text and file reads via `cr_strip="strip"`.

### UPDATED: python/step_7a.py

- Replace `_read_kv` with `larch_io.read_kv(..., first_match=True, cr_strip="strip", on_error_default=False)`.
- Preserve default return behavior on missing files only; propagate read errors on existing unreadable files.

### UPDATED: python/plan_quality.py

- Replace `_atomic_write` with `larch_io.atomic_write`.
- Replace `_parse_kv_stdout` with `larch_io.parse_kv`.
- Preserve parent creation and replacement behavior.

### UPDATED: python/run_logs.py

- Replace `_atomic_write` with `larch_io.atomic_write` using the `.manifest-` temp prefix where needed.
- Replace `_read_kv_file` / `_read_state_kv` internals with `larch_io.read_kv(..., first_match=True, errors="strict", on_error_default=True)`.
- Preserve first-match behavior, empty-string defaults, and strict UTF-8 decode-failure → `""` contract.
- Keep non-KV JSON and manifest logic unchanged.

### UPDATED: python/review_aggregate.py

- Replace `_read_text`, `_write_text`, `_atomic_write`, and `_kv_parse`.
- Use `replace_method="move"` for the current `shutil.move` atomic-write behavior.
- Preserve missing-file and exception behavior for reads.

### UPDATED: python/execution_issues.py

- Replace `_read_kv` with `larch_io.read_kv(..., first_match=True, cr_strip="strip", on_error_default=False, default="")`.
- Preserve empty-string defaults on missing files; propagate read errors on existing unreadable files.

### UPDATED: python/implement_dispatch.py

- Replace `_parse_kv` with `larch_io.parse_kv(..., first_wins=True, key_pattern=r"^[A-Z0-9_]+$")`.
- Replace `_read_kv_file` with `larch_io.read_kv`.
- Replace `_session_get` with `larch_io.read_kv(..., first_match=True)` without `cr_strip` (`cr_strip="none"`) to match current prefix scan.
- Replace `_write_text_atomic` with `larch_io.atomic_write` preserving sibling `path.name + ".tmp"` naming (no pid) and parent creation.
- Do not fold `_write_bytes_atomic` into `larch_io` unless the final helper explicitly supports bytes without expanding scope.
- Add parity coverage for duplicate-key stdout envelope parsing.

### UPDATED: python/file_oos.py

- Replace `_read_kv_file` with `larch_io.read_kvs(..., cr_strip="strip", default={})` (last-wins default); do **not** pass `reject_symlink` so symlink targets are followed when `is_file()` is true.
- Preserve missing-file `{}`, `errors="replace"` read semantics, and CRLF value stripping via `cr_strip="strip"`.
- Delete the local helper after repoint.

### UPDATED: python/stall_recovery.py

- Replace `read_kv` implementation with `larch_io.read_kv(..., first_match=False, cr_strip="strip", on_error_default=False)` or a thin re-export preserving the public name.
- Replace `write_kvs` with `larch_io.write_kvs` preserving insertion-order write behavior and newline format.
- Preserve last-match `read_kv` behavior and propagate `OSError` from existing unreadable files (default only for non-files).
- Add duplicate-key parity test in `python/test_stall_recovery.py` or `python/test_larch_io.py`.

### UPDATED: python/review_and_fix.py

- Replace `_read_text`, `_write_text`, `_append_text`, `_parse_env_lines`, and `_parse_env_file`.
- Replace `_parse_env_lines` with `larch_io.parse_kv(..., skip_empty_key=True)` (last-wins default).
- Replace `_env_get` with `larch_io.parse_kv(larch_io.read_text(path, default=""), skip_empty_key=True).get(key, default)` only; **do not** route `_env_get` through `read_kv(..., first_match=True)` because env files use last-wins duplicate-key semantics.
- Replace `_session_get` with `larch_io.read_kv(..., first_match=True, default=default, cr_strip="none")` without CR mutation (preserve raw RHS bytes).
- Use `read_text(default="")` for current missing-file behavior.
- Preserve skip-empty-key behavior where the local parser rejects empty keys.

### UPDATED: python/session_env.py

- Replace `_atomic_write` with `larch_io.atomic_write(..., nofollow=True, exclusive=True, mode=..., create_parent=..., temp_name=path.with_suffix(path.suffix + ".tmp")` or equivalent fixed sibling `.tmp` temp) so behavior matches today's `with_suffix` sibling temp, **shared pre-unlink before `O_EXCL`**, `O_CREAT|O_EXCL` (+ `O_NOFOLLOW`), and `fchmod` contract covered by `test_session_env.py`; do not substitute mkstemp-style random temp names.
- Replace `_kv_text` with `larch_io.format_kvs` (must accept iterable tuple rows used during finalize restore).
- **Keep `_read_kv_file_text` local** as the sole loader for session-env KV file bodies; it must continue to reject any `\r` in the whole file with `ValueError` per `test_session_env.py`.
- Replace `_read_kv_raw` with `larch_io.parse_kv(_read_kv_file_text(path), skip_comments=True)` (last-wins default; no `cr_strip` on values).
- Replace `_parse_text_kv` call sites (e.g. stale-plugin stdout parse) with `larch_io.parse_kv(text, skip_comments=True)` and delete `_parse_text_kv`.
- Keep `_read_first_raw_key` as a **local line scan** over `_read_kv_file_text(path).splitlines()` without comment skipping (do not route through `parse_kv(..., skip_comments=True)` or `kv_value` with comment skipping).
- Route any other raw-key reads that depended on `_read_kv_raw` through the repointed helper above.
- Keep shell parsing and allowlist validation local.
- Preserve all symlink refusal behavior and `O_EXCL` temp-create hardening.

### UPDATED: python/design_postplan.py

- Replace `_parse_kv` with `larch_io.parse_kv` (last-wins default).
- Replace `_write_result_env` with a bool-return wrapper over `larch_io.write_kvs(path, kvs, atomic=False, create_parent=False)` that catches `OSError` and returns `False` on failure, `True` on success; preserve dict insertion-order rows and empty-dict → empty file (not a lone `\n`).
- Delete both local helper definitions after repoint.

### UPDATED: python/ci_monitor.py

- Replace `_parse_kv_output` with `larch_io.parse_kv(..., strip_value=True, skip_empty_key=True)`.
- Preserve current last-wins behavior.

### UPDATED: python/plan_review_panel.py

- Replace `_parse_kv` with plain `larch_io.parse_kv` (last-wins default, no `key_pattern`, no `first_wins`).
- Preserve current overwrite behavior on duplicate keys.

### UPDATED: python/plan_review_round.py

- Replace `_parse_kv` with `larch_io.parse_kv` (last-wins default, no `key_pattern`, no `first_wins`), matching `plan_review_panel.py`.
- Delete the local `_parse_kv` helper after all call sites repoint.
- Drop any imports that become unused.
- Preserve stdout envelope parsing behavior on duplicate keys (last value wins).

### UPDATED: python/preflight.py

- Replace `_read_kv_lines` with `larch_io.parse_kv`.
- Replace `_write_text` with `larch_io.write_text(..., create_parent=True)`; preserve parent creation via the shared helper.

### UPDATED: python/pr_body.py

- Replace path-based `_read_kv` with `larch_io.read_kv(..., first_match=True, cr_strip="strip", on_error_default=False, default="")`; missing file returns `""` via `default=""`.
- Replace the nested stdout `_read_kv(text, key)` helper with `larch_io.kv_value(text, key, default="N/A")`.
- Delete the hand-rolled path loop after repoint.

### UPDATED: python/final_report.py

- Remove `pr_body._read_kv` private import alias.
- Import and call `larch_io.read_kv(..., first_match=True, cr_strip="strip", on_error_default=False)` directly with the same kwargs as `pr_body._read_kv`.
- Update any tests that depended on the `pr_body._read_kv` indirection.

### UPDATED: python/clarify.py

- Replace `_write_text` internals with `larch_io.write_text` where non-atomic string writes are safe.
- Replace `_write_text_file` with `larch_io.atomic_write(..., prefix=f".{path.name}.", create_parent=True)` plus a local pre-check that raises `ClarifyValidationError` on directory/symlink paths (preserve current validation and error wrapping); do not repoint `_write_text_file` to plain `write_text`.
- Replace `_write_result_env` with `larch_io.atomic_write` fed by `larch_io.format_kvs(rows)` (iterable tuple rows), preserving symlink pre-check, newline-in-value rejection, mkstemp-style `prefix=f".{destination.name}."`, and `os.replace` semantics; do not use plain `write_kvs` or non-atomic write here.
- Preserve string-path support at call sites.

### UPDATED: python/report_tokens_cost.py

- **Keep the float-specific `_parse_kv` loop local** so duplicate keys keep the last parseable float and later non-float values do not overwrite a prior valid float (`KEY=1.0` then `KEY=bad` still yields `1.0`); do not pre-parse to a string dict via `larch_io.parse_kv` before float conversion.
- Keep cost-domain conversion logic local.

### UPDATED: python/voting.py

- Replace the single-key `_parse_kv(output, key)` helper with `larch_io.kv_value`.
- Preserve first-match behavior and empty-string default.

### UPDATED: python/progress_report.py

- Replace `_read_simple_env` with `try`/`except OSError` around `larch_io.read_text(path, errors="replace", default="")` returning `{}` on read failure, then `larch_io.parse_kv(text)` (last-wins default; no comment skipping; preserve `partition("=")`-style acceptance via default `parse_kv`); delete the local helper.
- Leave `_read_env_file` local (shell `export` / `shlex` / key-regex behavior stays domain-specific).

### UPDATED: python/test_bootstrap.py

- Update private `_parse_kv` references if `bootstrap._parse_kv` is deleted.
- Prefer assertions through `larch_io.parse_kv` or public bootstrap behavior.
- Replace the `bootstrap._atomic_text` monkeypatch with `larch_io.atomic_write` (or a public-behavior assertion) so routing-write failure simulation still exercises the bootstrap path after `_atomic_text` deletion.

### UPDATED: python/test_admission.py

- Replace the `admission._atomic_text` monkeypatch with `larch_io.atomic_write` (or assert via public `admission.fork_env_main` behavior) so caller-env write-failure simulation still exercises the admission path after `_atomic_text` deletion.

### UPDATED: python/test_session_env.py

- Update monkeypatches that target `session_env._atomic_write`.
- Patch `larch_io.atomic_write` or test public behavior instead.
- Preserve coverage for mode, parent-creation, symlink refusal, `O_EXCL` temp-create behavior, stale-sibling-temp pre-unlink, whole-file CR rejection via `_read_kv_file_text`, comment skipping on `_read_kv_raw`, and no comment skipping on `_read_first_raw_key`.

### UPDATED: python/test_file_oos.py

- Add focused parity coverage for `file_oos._read_kv_file` repoint: missing-file `{}`, symlink-follow when the symlink target is a regular file, and CRLF stripping on values.

### UPDATED: python/test_plan_review.py

- Add a focused parity test that `plan_review` atomic sidecar writes with `create_parent=False` do not auto-create missing parent directories (preserve current `_write_atomic` failure mode).

### MAY_UPDATE: python/progress_report.py

- `_read_env_file` remains local unless `larch_io.read_kvs` can preserve shell-style `export`, `shlex`, and key-regex behavior without making the shared IO module domain-specific.

### MAY_UPDATE: python/agents.py

- Repoint `_read_text` and `_review_atomic_write_text` only if behavior matches the shared helper exactly.
- Avoid broad changes in this large module unless the replacement is mechanical and low risk.
- **Defer by default** in this PR: `_read_text` accepts `None` and returns `""` without raising; `_write` / `_append` / `_review_atomic_write_text` are not verified parity-safe yet.

### MAY_UPDATE: python/dirty_tree.py

- Leave `_write_atomic` local unless `larch_io.atomic_write` intentionally supports bytes.
- Do not expand the helper API solely for this byte writer.

## Edge cases

- Duplicate keys must keep each caller’s first-wins or last-wins behavior.
- Missing files must keep each caller’s current default.
- Invalid UTF-8: `run_logs` uses strict decode with empty fallback; other sites keep `errors="replace"` at the **read** layer where used today, not on `parse_kv`.
- `on_error_default` must be set per call site: `True` only for best-effort readers (`run_logs`, `design_lifecycle._read_env_value`, `bootstrap._read_simple_kv`); `False` for `pr_body`, `final_report`, `step_7a`, `execution_issues`, and `stall_recovery.read_kv`.
- `design_lifecycle._read_env_value_last`, `_read_env_values`, `_read_simple_env`, and `progress_report._read_simple_env` must keep `OSError` → default/`{}` fallback via local `try`/`except OSError` around `read_text`, not bare repoints that propagate read failures.
- `cr_strip` must be set per call site; explicit mapping:
  - `"rstrip"`: `bootstrap._parse_kv`
  - `"suffix"`: `bootstrap._read_simple_kv`
  - `"strip"`: `oos_filer` (stdout and file), `pr_body`, `final_report`, `execution_issues`, `stall_recovery.read_kv`, `file_oos`, `step_7a`
  - `"none"`: `implement_dispatch._session_get`, `review_and_fix._session_get`, `session_env` raw reads (values pass through unchanged after load)
- Session-env whole-file CR rejection stays in local `_read_kv_file_text`; generic `read_kvs` `reject_cr=True` is available but not a substitute on session-env repoints.
- Session-env `_read_kv_raw` and stale-plugin stdout parsing must use `skip_comments=True`; `_read_first_raw_key` must not skip `#` comment lines.
- Empty keys must stay accepted or rejected per call site via `skip_empty_key` (`review_pipeline`, `review_and_fix`, `ci_agentic_fix`, `ci_monitor` reject).
- `KEY=` empty RHS must map to default only where `_read_env_value` semantics apply (`empty_value_means_default=True`).
- `design_lifecycle._read_env_value_last` and `_read_env_values` must ignore empty duplicate values rather than letting them overwrite prior nonempty values; dict-based `read_kv`/`read_kvs` cannot preserve this and these readers stay local line iterators over `read_text`.
- `design_lifecycle._read_simple_env` must preserve allowlist filtering and reject values containing embedded `\n` or `\r` after `parse_kv`.
- `review_and_fix._env_get` must use last-wins `parse_kv` semantics, not `read_kv(..., first_match=True)`.
- `report_tokens_cost` must keep last-valid-float semantics on duplicate keys with intervening non-float values; keep the float loop local.
- Key regex filters must stay exact (`implement_dispatch` first-wins + uppercase pattern; `plan_review_panel` and `plan_review_round` have no filter).
- Shell-style env parsing must not be flattened into generic KV parsing unless behavior stays identical.
- Read-side symlink refusal must be preserved for `plan_review`, `design_lifecycle`, and `bootstrap._read_simple_kv`; `file_oos._read_kv_file` must **not** reject symlinks.
- Atomic write temp names can matter in tests, logs, or cleanup paths (`research` pid suffix; `implement_dispatch` bare `.tmp`; `session_env` fixed sibling `with_suffix(".tmp")`).
- `plan_review._write_atomic` must not auto-create parent directories (`create_parent=False`).
- `session_env` symlink refusal, `O_EXCL` temp creation, stale-temp pre-unlink, file mode behavior, and iterable `format_kvs` finalize restore must remain intact.
- `review_aggregate` currently uses `shutil.move`; preserve that path with `replace_method="move"`.
- `design_lifecycle._write_kv_file`, `design_postplan._write_result_env`, and `design_publish._write_result_env` are intentionally non-atomic with bool `OSError` swallow via local wrappers around `write_kvs(..., atomic=False)`.
- `clarify._write_text_file` and `clarify._write_result_env` must remain atomic and symlink-refusing; plain `write_text` / non-atomic `write_kvs` are not valid replacements for those writers.
- `write_kvs` itself raises `OSError`; bool-return success/failure is owned only by local wrappers.

## Failure modes

- A shared default can silently change a wire parser (mitigated by `skip_empty_key=False` default, explicit per-site `cr_strip`, and explicit per-site kwargs).
- Deleting private helpers can break tests that monkeypatch them (`session_env`, `final_report`, `test_bootstrap._atomic_text`, `test_admission._atomic_text`).
- Broad refactors can leave unused imports and fail `py-lint`.
- A generic helper with too many knobs can become harder to read than the copies.
- Repointing shell env readers can change quoting semantics.
- Weaker `atomic_write` without `exclusive=True`, missing pre-unlink, or wrong sibling `temp_name` can introduce symlink/temp-file races or `FileExistsError` on session env writes and launcher resume.
- `on_error_default=True` at strict readers can hide I/O failures.
- Dropping `try`/`except OSError` on `design_lifecycle` / `progress_report` best-effort env readers can abort design recovery or postplan paths on unreadable sidecars.
- Dict-based `read_kv`/`read_kvs` on `design_lifecycle` last-nonempty readers can change env precedence for empty duplicate lines.
- Homogenizing `cr_strip` modes can change RHS bytes on repoint (mitigated by explicit per-site `cr_strip` mapping).
- Omitting `skip_comments=True` on `session_env._read_kv_raw` / stale-plugin stdout parse can parse commented lines as keys.
- Routing `review_and_fix._env_get` through first-match `read_kv` can return stale scout status on duplicate env keys.
- String-dict-then-float conversion in `report_tokens_cost` can drop last-valid floats when later duplicates are non-numeric.
- Mapping-only `format_kvs` would break session-env finalize restore tuple ordering.
- Bool-return logic on `write_kvs` itself would desync wrapper semantics from `design_lifecycle` / `design_postplan` / `design_publish` callers.
- Leaving `plan_review_round._parse_kv` or `session_env._parse_text_kv` in place defeats the one-definition acceptance criterion.
- Default `create_parent=True` on `plan_review` atomic writes can mask missing-directory failures.

## Testing strategy

- Add `python/test_larch_io.py` for the shared helper contract, including strict UTF-8, empty-key, symlink-reject, `reject_cr`, `cr_strip` mode divergence, `empty_value_means_default`, iterable `format_kvs`, `exclusive` atomic-write cases, and stale fixed-temp pre-unlink before `O_EXCL`.
- Assert `write_kvs` raises `OSError` on failure; test bool-return swallow on `design_lifecycle._write_kv_file` / `design_postplan._write_result_env` / `design_publish._write_result_env` wrappers (existing or added focused tests), not inside `test_larch_io.py`.
- Add `python/test_file_oos.py` parity cases for missing-file `{}`, symlink-follow reads, and CRLF stripping after `_read_kv_file` repoint.
- Add `python/test_plan_review.py` parity case that atomic writes do not create missing parent dirs (`create_parent=False`).
- Update `python/test_admission.py` monkeypatch target after `admission._atomic_text` removal.
- Add or extend session-env tests for `_read_kv_raw` comment skipping, `_read_first_raw_key` non-comment behavior, and stale-sibling-temp pre-unlink on `exclusive=True` writes.
- Run focused tests first:
  - `python3 -m pytest python/test_larch_io.py python/test_bootstrap.py python/test_session_env.py python/test_stall_recovery.py python/test_file_oos.py python/test_admission.py python/test_plan_review.py`
  - `python3 -m pytest python/test_review_pipeline.py python/test_review_aggregate.py python/test_review_and_fix.py python/test_review_tally.py python/test_run_logs.py python/test_implement_dispatch.py`
- Run a duplicate-helper grep and review only expected exceptions:
  - KV test helpers.
  - byte-only atomic writers if left local (`dirty_tree._write_atomic`).
  - shell-env parsers if behavior is domain-specific (`progress_report._read_env_file`, shell-decoding readers in `design_lifecycle` / `session_env` / `bootstrap`).
  - `_read_kv_file_text` in `session_env` (CR-rejection loader).
  - `_read_first_raw_key` line scan in `session_env` (no comment skipping).
  - `report_tokens_cost._parse_kv` (float-specific duplicate semantics).
  - `design_lifecycle._read_env_value_last` and `_read_env_values` (last-nonempty line iterators).
  - **deferred highest-ROI text-IO clones in `agents.py`**: `_read_text` (None-path semantics), `_write`, `_append`, `_review_atomic_write_text`.
- Run required checks:
  - `make py-lint`
  - `make py-test`
  - `make lint`

## Acceptance

- One definition per shared helper lives in `python/larch_io.py`. All duplicate `parse_kv` / `read_kv` / `read_kvs` / `kv_value` / `format_kvs` / `write_kvs` / `atomic_write` / `read_text` / `write_text` / `append_text` copies are deleted after their call sites repoint, except the documented parity exceptions kept local (see Edge cases): `session_env._read_kv_file_text`, `report_tokens_cost._parse_kv`, `design_lifecycle._read_env_value_last` / `_read_env_values`, shell-env readers, `dirty_tree._write_atomic`, and the deferred `agents.py` text-IO clones.
- Behavior is unchanged at every repointed call site: duplicate-key first/last-wins, missing-file defaults, per-site `cr_strip` mode, `skip_empty_key`, `on_error_default`, `empty_value_means_default`, symlink refusal, `O_EXCL` temp-create with stale-temp pre-unlink, `shutil.move` vs `os.replace`, and `errors=` decoding all match the prior local helper.
- On-disk wire formats are unchanged: the `KEY=value` stdout grammar and `.sh` env-file byte format are preserved. Refactor the parsing and writing, not the format. `write_kvs` raises `OSError`; bool-return success/failure stays in local wrappers only.
- `normalize_reviewer_label` is NOT moved; it stays in `python/review_pipeline.py`.
- `python/test_larch_io.py` covers the shared contract; `test_bootstrap`, `test_admission`, `test_session_env`, `test_file_oos`, and `test_plan_review` are updated for moved monkeypatch targets and per-site parity.
- `make py-lint`, `make py-test`, and `make lint` are green; no unused imports remain after local-copy deletion.

diff_added: 600
diff_deleted: 625
mechanical_churn: true
diff_lines: 1225

## Test plan
(no test plan section in plan-file)
