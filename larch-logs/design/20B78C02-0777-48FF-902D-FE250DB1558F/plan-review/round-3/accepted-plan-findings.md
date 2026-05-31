### FINDING_1: Prelude doc fence double-counts canonical guarded-source line
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: A planned change replaces the Bash block prelude example in `skills/implement/SKILL.md` (~116–121) with the same byte-identical canonical guarded-source line used in executable fences elsewhere. If `scripts/test-implement-timing-rehydration.sh` still asserts `grep -Fxc` of that line equals 40 (assertion (a)), the prelude prose fence adds an 11th matching line (37 post–Step-0 + 3 pre-bootstrap + 1 prose = 41). CI would fail after an otherwise correct SKILL migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Set expected guarded-source count to 41, or carve the prelude fence out of the cardinality check, or document the prelude with a non-matching illustrative line
  - From Cursor-Innovation: Count only executable fences (e.g. awk fence scanner like Invariant C, or exclude the prelude line range), assert >=40 with a separate ==1 doc check, or use a non-identical commented example in the prelude
  - From Cursor-Pragmatic: Set the expected guarded-source count to 41, or exclude the prose fence from the grep (e.g., assert 40 outside the prelude section only)


### FINDING_2: Resume-tail `emit_plugin_root_env` writes unvalidated session-env into a sourceable file
- **Reviewer(s)**: Cursor-dyn-writer-source-safety
- **Severity**: important
- **Concern**: The proposed `emit_plugin_root_env` in `scripts/write-session-env.sh` (used from resume-tail paths in `scripts/implement-bootstrap.sh` ~563–586) would trust `LARCH_CLAUDE_PLUGIN_ROOT=` from `session-env.sh` and write it into a dot-sourceable `plugin-root.env` without re-validating the value first. A hostile or malformed line in `session-env.sh` could become executable shell when sourced—worse than the current awk-to-variable extraction path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-writer-source-safety: Inside emit_plugin_root_env, reuse the existing ^[A-Za-z0-9_./~+-]{1,512}$ plus absolute-path checks from write-session-env.sh:136-145 on the value argument; skip the write when validation fails (same as empty/missing)

