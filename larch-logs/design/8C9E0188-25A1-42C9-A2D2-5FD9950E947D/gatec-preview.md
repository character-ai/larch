## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

Build separate, production-shaped implement and design test-fixture contracts. Preserve raw file construction whenever a test verifies wire shape, absence, duplication, corruption, symlinks, or production-writer output.

## Files to modify/create

### NEW: python/tests/__init__.py

- Add the empty package marker required for unambiguous `tests.support.*` imports.
- Do not add another flat `python/test_*.py` module.

### NEW: python/tests/support/repo_contract.py

- Move the repository-root contract to this dependency-free module.
- Export the repository root and `repo_root()` using the path rule appropriate to this module.
- Make both `test_support` and `tests.support.session` depend on this module; `session.py` must not import `test_support`.

### NEW: python/tests/support/session.py

- Add deterministic helpers returning the created path:
  - `write_session_env(implement_tmpdir, overrides=..., omit=...)`
  - `write_design_source_env(design_tmpdir, overrides=..., omit=...)`
  - `seed_plan`, `seed_feature_description`, and `seed_run_params`
  - `make_implement_tmpdir` and `make_design_tmpdir`
- Keep `write_session_env` scoped to plain `session-env.sh` `KEY=value` files. Its exact implement baseline must match the existing dispatch `_session` fixture:
  - `CURSOR_PRESENT=false`
  - `CODEX_BINARY_FOUND=true`
  - `CURSOR_BINARY_FOUND=true`
  - `LARCH_CLAUDE_PLUGIN_ROOT=<repo root>`
  - `REPO_ROOT=<repo root>`
- Keep `CODEX_PRESENT` and `CLAUDE_PLUGIN_ROOT` absent from the implement baseline. Allow implement overrides to set either presence key independently from either binary-found key.
- Treat `write_session_env` as a fixture writer, not a production-writer allowlist: accept any syntactically valid environment key in `overrides`, including reader-only test keys such as `MODE`, `REPO`, `WORKFLOW_PATH`, and `LARCH_RUN_ID`. Reject malformed key names and newline, carriage-return, or NUL-bearing values.
- Make `write_design_source_env` emit the production-style `source-env.sh` shell format and restrict its keys to the design writer contract. Its baseline must contain `DESIGN_TMPDIR`, `SESSION_TMPDIR`, `SESSION_ID`, `REPO_ROOT`, and `CLAUDE_PLUGIN_ROOT`; it must not write `LARCH_CLAUDE_PLUGIN_ROOT`. Keep optional design values, including `REPO`, tool flags, and run metadata, absent unless explicitly requested.
- Do not add `CODEX_PRESENT` or `CURSOR_PRESENT` to design source fixtures: they are not persisted by `WRITE_DESIGN_ENV_KEYS`. Tests that need those non-writer shapes must retain raw fixtures.
- Make overrides replace a baseline entry in place, reject an override/omit conflict, and support explicit omission of baseline keys for negative and sparse fixtures. Emit one entry per key, deterministic ordering, and one final newline.
- Make `make_implement_tmpdir(tmp_path, ...)` create and return exactly `tmp_path / "impl"`. Seed `plan.txt`, `feature-description.txt`, and `session-env.sh` there; seed `run-params.json` only when requested.
- Make `make_design_tmpdir(tmp_path, ...)` create and return exactly `tmp_path / "design"`. Seed `source-env.sh` there with the design contract and seed `run-params.json` only when requested.
- Make `seed_run_params` write the exact schema-v3 payload produced by `write_run_params_main`: `schema_version: 3`, all four request booleans `false`, and `difficulty_override: ""`.
- Keep all helper side effects under the caller-provided pytest temporary directory.

### UPDATED: python/test_support.py

- Import root values from `tests.support.repo_contract` and preserve the existing flat `ROOT`, `CLI`, and `repo_root` public API.
- Re-export the session helpers only after the root contract is available.
- Do not retain duplicate root constants or session-default mappings.
- Maintain a one-way import graph: `repo_contract` has no support imports; `session` imports only `repo_contract`; `test_support` re-exports `session`.

### UPDATED: python/tests/support/test_foundation.py

- Extend focused support coverage for repository-root ownership, import compatibility, implement and design artifact layouts, returned paths, deterministic output, override replacement, explicit omission, separate root aliases, and schema-v3 run parameters.
- Assert that implement overrides accept valid additive reader keys while malformed keys and unsafe values are rejected.
- Assert that sparse implement fixtures can omit the complete baseline before adding only requested keys.
- Assert that tool-presence keys remain distinct from binary-found keys and that opposite-contract aliases are absent by default.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Import shared helpers through `test_support`.
- Remove the private `_session` builder and replace every normal `_session(tmp_path)` setup with `make_implement_tmpdir(tmp_path)`.
- Preserve the `tmp_path / "impl"` basename and its three seeded artifacts at every migrated call site.
- Convert ordinary model-option and session replacements to `write_session_env` overrides or omissions.
- Retain raw `session-env.sh` writes for malformed values, missing-key fallback, duplicate/first-match behavior, or intentionally altered file shape.
- Remove migrated `parents[N]` plugin-root derivations now supplied by the implement builder.

### UPDATED: python/tests/state/test_session_env.py

- Use `make_design_tmpdir` and `write_design_source_env` only for normal design-consumer fixtures.
- Use implement helpers for normal plain `session-env.sh` fixtures, and reuse `seed_run_params` for valid persisted parameter files.
- Keep direct writes for parser input, carriage-return injection, duplicate keys, symlinks, missing-key cases, precedence tests, and all `write-env`/`write-design-env` production-writer assertions.
- Keep production writer assertions independent of helper formatting and verify the helper does not introduce design-only or implement-only aliases.

### UPDATED: python/tests/state/test_bootstrap.py

- Align every migrated fixture’s artifacts with the directory passed as `implement_tmpdir`.
- Use `make_implement_tmpdir` only when the test switches its `implement_tmpdir` binding to the helper’s returned `tmp_path / "impl"` path.
- For tests that intentionally retain `implement_tmpdir=str(tmp_path)`, use `seed_plan`, `seed_feature_description`, and `write_session_env` directly on `tmp_path`; do not seed under `tmp_path / "impl"`.
- Replace ordinary repeated `plan.txt`/`feature-description.txt` setup with those aligned seed helpers or the aligned implement builder.
- Use `write_session_env` for ordinary bootstrap and resume fixtures.
- Preserve narrow raw fixtures for omitted keys, symlinks, precedence, legacy routing values, and source text whose exact content is under test.
- Do not change bootstrap behavior or persisted session contracts.

### UPDATED: python/tests/state/test_closeout.py

- Use `write_session_env` for ordinary run-id setup.
- Keep parametrized raw session, ship, and finalize state text where source precedence, exact absence, or parsing behavior is asserted.
- Preserve closeout subprocess stubs and assertions.

### UPDATED: python/tests/report/test_final_report.py

- Refactor `_write_minimal_state` and ordinary plan-coverage setups to use the shared implement session writer with per-test overrides.
- For intentionally sparse report inputs, omit every implement baseline key before adding only the required keys, such as `REPO` and `MODE`.
- Replace repeated canonical `REPO_ROOT`, `REPO`, and `MODE` session files without changing report inputs.
- Retain malformed, deliberately incomplete, or corrupted artifacts used by failure-path tests.

## Edge cases

- Implement and design builders must remain separate contracts: filenames, shell format, defaults, root aliases, and allowed keys must not bleed across them.
- Implement fixture overrides may add any safe, syntactically valid `KEY=value` reader input; design source fixtures remain restricted to production writer keys.
- Defaults must never mask a test’s intended missing-key behavior; use `omit` or retain raw setup.
- Bootstrap artifacts must be written into the exact `implement_tmpdir` consumed by each test.
- Repeated parameterized tests must receive isolated paths and fresh mappings.
- Paths containing spaces must remain valid values.
- Resolve Piece 1 rebase conflicts through the shared support API only; do not expand this piece into CLI or runner migration.

## Failure modes

- Returning the parent instead of `tmp_path / "impl"` or failing to seed its three dispatch artifacts breaks dispatch assumptions.
- Seeding `tmp_path / "impl"` while bootstrap reads `tmp_path` leaves required artifacts invisible.
- An implement writer restricted to production writer keys prevents ordinary reader fixtures from setting `MODE`, `REPO`, and similar inputs.
- A shared baseline that writes design keys into implement fixtures, or vice versa, can make tests pass against the wrong production contract.
- Re-export imports that cycle through `test_support` can fail collection with partially initialized modules.
- Appending overrides can change first-match `KEY=value` behavior.
- A stale run-params payload can drift from schema v3.

## Testing strategy

- Run the focused suites:
  - `python/tests/support/test_foundation.py`
  - `python/tests/implement/test_implement_dispatch.py`
  - `python/tests/state/test_session_env.py`
  - `python/tests/state/test_bootstrap.py`
  - `python/tests/state/test_closeout.py`
  - `python/tests/report/test_final_report.py`
- Cover exact implement and design defaults, root-alias absence, presence-versus-binary independence, valid additive implement overrides, override replacement, explicit omission, sparse fixture construction, seed contents, isolated directories, returned paths, and bootstrap path alignment.
- Run Ruff, Pylint, and Pyright against only changed Python files.
- Run the flat-test lint to confirm `python/test_support.py` remains the sole root exemption.
- Check duplicate-code findings across the changed test set to confirm `_session` and repeated seed blocks were removed.

difficulty: MODERATE
diff_added: 300
diff_deleted: 400
mechanical_churn: true
diff_lines: 700
