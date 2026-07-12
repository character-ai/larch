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


