### FINDING_1: Result-env path needs trusted prevalidation and allowed-root enforcement
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Cursor-dyn-Result Env Boundary Auditor, Codex-dyn-Result Env Boundary Auditor
- **Severity**: major
- **Concern**: Required result-env writes must remain inside the allowed tmpdir boundary, use the existing trusted merge-env validation and atomic-write mechanisms, and be validated before `run_ship` or other mutations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Refuse result-env work unless _tmpdir_under_allowed_root(ctx.tmpdir) is true; then validate with the same trusted-root helper stack as bgjob merge envs (prefer bgjob.model.validate_merge_result_env). Add a ship test mirroring the invalid-tmpdir journal case with --result-env-path set.
  - From Cursor-Arch: G-Fix-1 / G-IO-1: delegate path validation to bgjob.model.validate_merge_result_env(path, tmpdir=Path(ctx.tmpdir)) and write via larch_io.atomic_write/format_kvs; keep only ship-specific KV rendering in emit_result.
  - From Codex-Arch: Validate and canonicalize the result-env path immediately after argument parsing, before run_ship or other mutations; add a test proving run_ship is not called for invalid paths 1. **[security]** Validate `--result-env-path` before `run_ship`, not only during final emission.
  - From Cursor-Pragmatic: Add the same _tmpdir_under_allowed_root(ctx.tmpdir) precondition used for journaling: refuse result-env writes when it fails, before path validation or atomic write.
  - From Cursor-dyn-Result Env Boundary Auditor: Reuse bgjob.model.validate_merge_result_env (or dispatch_commit_route._safe_merge_env) then larch_io.trusted_atomic_write(..., root=Path(ctx.tmpdir), mode=0o600); do not mkdir parents outside that validated path
  - From Cursor-dyn-Result Env Boundary Auditor: Gate required result-env writes on _tmpdir_under_allowed_root(ctx.tmpdir) and fail closed when --result-env-path is set and the gate fails
  - From Codex-dyn-Result Env Boundary Auditor: Use `larch.io.trusted_atomic_write(..., root=ctx.tmpdir, mode=0o600)` and retain the no-symlink component validation.
  - From Codex-dyn-Result Env Boundary Auditor: Required result-env writes should fail closed when the allowed-root gate fails, not silently skip like journaling.


### FINDING_4: CI result-env key pairing must match route-exit semantics
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Result-env emission must preserve the route-exit pairing rules and avoid contradictory CI keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror dispatch_ship pairing in ship_result env emission: always emit CI_ERRORS_FILE= and FAILED_JOBS_COUNT=; emit CI_ERRORS_DISTILL_CLASS only when the file value is empty; add a test for success and distill-failure shapes


### FINDING_2: Reject lexical `..` result-env paths during prevalidation
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: Path prevalidation remains incomplete for lexical `..` paths, which can cause the validator’s lexical parent loop to fail to reach the resolved root and hang at `/`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Reject result-env paths containing `..` before calling the validator, and add this case to the planned preflight tests


### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_result.py
- **Concern**: [SCOPE-REDUCTION] Blanket uppercase key rendering drifts from route-exit wire names. Scenario: `dispatch_ship` handoff emits lowercase ledger keys such as `ledger_ready=true` (see `test_implement_dispatch.py`), while repair/CI keys are uppercase. Uniform uppercasing of JSON keys would emit `LEDGER_READY` and break parity with established handoff vocabulary piece 2 must consume.
- **Proposed resolution**: Name an explicit mixed-case key map aligned with `dispatch_ship` (`FAILED_RUN_ID`, lowercase `ledger_*`, uppercase repair/CI keys, plus documented `outcome` casing) instead of uppercasing every JSON field.


