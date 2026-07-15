### FINDING_1: `bgjob start` bypasses tmpdir normalization
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Codex-dyn-Tmpdir Ast Ratchet Auditor
- **Severity**: major
- **Concern**: `start_main` calls `_build_spec` with raw `args.tmpdir`, so an empty argument can become `Path("")` and resolve to the cwd while the baseline reason only covers the adapted path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Empty --tmpdir on bgjob start still hits Path(args.tmpdir) resolving to cwd while lint passes via baseline with a false reason Revise baseline reason to name both call paths and document start_main caller non-empty contract per G-Fix-1 or normalize tmpdir in start_main before _build_spec
  - From Cursor-Innovation: In ### UPDATED: python/larch/bgjob/cli.py add start_main preflight that resolves args.tmpdir with the same explicit-or-DESIGN-or-IMPLEMENT fallback chain as _adapt_tmpdir (without session mismatch logic), errors on missing, then calls _build_spec.
  - From Cursor-Requirements: Add an `UPDATED: python/larch/bgjob/cli.py` step for `start_main` only: normalize tmpdir before `_build_spec` using the same `str(args.tmpdir) or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")` pattern as `wait_main`, without editing `_build_spec`. Update the baseline reason to note adapt-fed versus start-fed callers.
  - From Codex-dyn-Tmpdir Ast Ratchet Auditor: Before `start_main` calls `_build_spec`, resolve the empty argument through `config.ENV_IMPLEMENT_TMPDIR` and fail when still empty; retain the single baseline only after that normalization, with a focused start-path regression test.


### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/lint/test_lint_tmpdir_arg_env_fallback.py
- **Concern**: [SCOPE-REDUCTION] Do not require unrelated `or` expressions to remain findings. Scenario: The exact rule flags only calls whose argument node is exactly `args.tmpdir`; enforcing a failure for `args.tmpdir or other_value` broadens the ratchet beyond the specified AST shape.
- **Proposed resolution**: Remove that case or assert unrelated BoolOp arguments are ignored; keep detection limited to the two exact nodes in the issue.


### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/bgjob/cli.py:24,64
- **Concern**: `start_main` still parses `--tmpdir` as required. Scenario: The plan-mandated omitted-`--tmpdir` regression case exits in argparse before the planned environment fallback runs.
- **Proposed resolution**: Call `_add_common_job_args` with `tmpdir_required=False` for `bgjob start`, then apply the planned fallback and missing-tmpdir error.

