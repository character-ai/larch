### FINDING_1: Implement tmpdir layout contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `make_implement_tmpdir` must return the `tmp_path/impl` directory and seed the artifacts expected by `_session`; returning the parent or omitting seeds breaks dispatch path assumptions.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Document and implement make_implement_tmpdir to mkdir tmp_path / "impl", seed artifacts there, and return that directory (same basename as today).
  - From Cursor-Pragmatic: Specify make_implement_tmpdir creates tmp_path/impl seeds the three artifacts and returns the impl Path; document the same contract in the test_implement_dispatch migration section.


### FINDING_3: Separate implement and design fixture contracts
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-dyn-Session Fixture Contract Auditor, Codex-Requirements, Codex-dyn-Session Fixture Contract Auditor
- **Severity**: major
- **Concern**: The planned shared baseline conflates implement `session-env.sh` and design `source-env.sh` formats, filenames, required keys, plugin-root aliases, and tool-presence fields, allowing migrated tests to pass while exercising the wrong production contract.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Specify make_design_tmpdir return path, subdirectory name, and default artifacts; keep production write-design-env and write-env tests on raw or CLI-generated fixtures.
  - From Codex-Arch: Include CODEX_PRESENT with a separate override from CODEX_BINARY_FOUND and test both presence keys
  - From Cursor-Innovation: Split IMPLEMENT_SESSION_DEFAULTS and DESIGN_SESSION_DEFAULTS; do not write LARCH_CLAUDE_PLUGIN_ROOT into design source-env or CLAUDE_PLUGIN_ROOT into implement session-env unless a test override requires it
  - From Codex-Innovation: Split implement and design defaults by artifact, and preserve raw setup for missing-key fallback tests.
  - From Cursor-Pragmatic: Scope write_session_env to implement session-env.sh plain KV only. Either keep design setup on production write-design-env or add a separate write_design_source_env export helper. State which files make_design_tmpdir creates and which writer each consumer uses.
  - From Cursor-dyn-Session Fixture Contract Auditor: Specify `make_design_tmpdir` outputs: design root, `source-env.sh` with `DESIGN_TMPDIR`, `SESSION_TMPDIR`, `SESSION_ID`, and optional `seed_run_params`; mirror `_base_design_writer_values` / `WRITE_DESIGN_ENV_KEYS`.
  - From Cursor-dyn-Session Fixture Contract Auditor: Document `variant="implement"|"design"` (or separate thin wrappers) with path + allowlist per production writer; keep production-writer subprocess tests on raw CLI output only.
  - From Codex-Requirements: Specify per-builder key sets, keep the opposite root key absent by default, and test both contracts.
  - From Codex-dyn-Session Fixture Contract Auditor: Define consumer-specific implement/design defaults from the production writer outputs, make optional keys absent by default, and add an explicit omit/unset mechanism. Keep raw fixtures for missing, malformed, duplicate, symlinked, and precedence-sensitive cases.


### FINDING_4: Avoid support-module circular imports
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Module-level re-exports in `test_support.py` combined with root imports from `tests.support.session` can expose partially initialized modules and fail test collection.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Keep ROOT/repo_root authoritative in one module (inline Path(__file__).resolve().parents[3] in session.py matching test_support.ROOT); place test_support re-exports at file end after ROOT is defined, or import session only inside lazy accessors.
  - From Codex-Arch: Move the repository-root contract to a lower-level support module, then have both modules depend on it
  - From Cursor-Innovation: Keep ROOT/repo_root in test_support; in session.py resolve the repo root locally (parents[3] from session.py) or import test_support only inside builder functions; document the one-way dependency in session.py
  - From Cursor-Pragmatic: Resolve repo root inside session.py with the same Path rule as test_support (no import from test_support). Limit test_support to re-exporting session symbols after both modules load or use lazy __getattr__ re-exports.
  - From Codex-Pragmatic: Define the root contract in a dependency-free module, or require root definitions before the re-export and prohibit import-time back-references.
  - From Cursor-Requirements: Pick one owner for ROOT or repo_root (keep Piece 1 test_support as owner). session.py imports that leaf only. test_support re-exports session helpers. Or add tests/support/repo_contract.py with no session imports.


### FINDING_1: Bootstrap tmpdir layout misaligned with dispatch `impl/` convention
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Many bootstrap tests set `implement_tmpdir=str(tmp_path)` and write `plan.txt` / `session-env.sh` at the `tmp_path` root, while `make_implement_tmpdir` always seeds `tmp_path/impl`. Replacing inline setup with `make_implement_tmpdir` without retargeting `implement_tmpdir` leaves artifacts under `impl/` while bootstrap still reads the parent directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `test_bootstrap.py` migration notes, require directory alignment: use `seed_plan`/`seed_feature_description`/`write_session_env` on the same path passed as `implement_tmpdir`, or switch `implement_tmpdir` to the path returned by `make_implement_tmpdir`; reserve `make_implement_tmpdir` for dispatch-style bindings only


### FINDING_2: `write_session_env` key acceptance / allowlist policy is underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan requires rejecting invalid keys and seeding an implement baseline that includes keys outside `WRITE_ENV_KEYS` (e.g. `CURSOR_PRESENT`), while migrated fixtures need additive overrides such as `MODE`, `REPO`, and other reader keys not in the implement baseline. If “reject invalid keys” is read as a `WRITE_ENV_KEYS`-only writer allowlist, baseline seeding, `_write_minimal_state`-style sparse fixtures, and ordinary per-test overrides will fail validation or force unintended raw rewrites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document that implement `write_session_env` accepts any `_KEY_RE`-valid key for overrides (value hygiene only), while `write_design_source_env` stays restricted to `WRITE_DESIGN_ENV_KEYS`; for minimal fixtures, require omitting every implement baseline key before writing sparse overrides such as `REPO`+`MODE` only
  - From Cursor-Innovation: Define an explicit implement allowlist (at minimum WRITE_ENV_KEYS plus fixture-only keys such as CURSOR_PRESENT used by migrated tests) and document which keys are production-writer vs fixture-only.
  - From Cursor-Requirements: Document that overrides may add any safe KEY=value pair not in the baseline (including REPO MODE WORKFLOW_PATH LARCH_RUN_ID) and that invalid-key rejection targets malformed names or unsafe values, not production-writer allowlist exclusivity


