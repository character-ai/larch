---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Default append must not create the clone progress tree before validating `current`
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: major
- **Concern**: The default `append_breadcrumb` path can still create `progress/<clone-hash>/` before it has confirmed a valid `current` pointer. That breaks the fail-silent contract for missing or invalid `current`, because a no-op write can leave behind orphan progress state instead of returning `False` with no side effects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Mandate `_open_verified_dir(clone_dir)` only for default `append_breadcrumb` (return `False` on `OSError`); read `current` via `_read_active_run_id_from_dirfd`; only then `_open_or_create_subdir` for the active run. Drop `_ensure_directory_fd` from the default-append path. Optionally `[SCOPE-REDUCTION]`: after `breadcrumb_line`, gate on `read_active_run_id(repo_root)` and delegate to `append_breadcrumb_for_run` so clone-open semantics stay aligned with the public reader`
  - From Codex-Arch: `Require `_open_verified_dir(clone_dir)` for `append_breadcrumb`, or explicitly preflight and bail before any directory creation; reserve `_ensure_directory_fd` for activation paths only`


### [Plan Review] FINDING_2

### FINDING_2: Default append should reuse the explicit override writer instead of duplicating the fd pipeline
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The plan re-specifies a second fd-append path for default writes instead of reusing the existing run-scoped helper. That duplicates logic already present in `append_breadcrumb_for_run`, which increases drift risk and weakens alignment with the accepted TOCTOU pin behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `The plan should describe default append as: validate with `breadcrumb_line`, return `False` when `read_active_run_id(repo_root)` is `None`, else call `append_breadcrumb_for_run(repo_root, run_id, skill, step, text)` unchanged. Keep the new fd-pin test on `append_breadcrumb` because it still exercises the production entrypoint`


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py:121-151
- **Concern**: [SCOPE-REDUCTION] Default `append_breadcrumb` clone open must use `_open_verified_dir` only, not `_ensure_directory_fd`. Scenario: The plan lists `_ensure_directory_fd` as the primary clone-dir opener for default `append_breadcrumb`, mirroring `append_breadcrumb_for_run`. `_ensure_directory_fd` mkdirs the clone-hash directory before `current` is validated. A call with no prior `activate_run` (missing clone or missing `current`) can return `False` yet leave `progress/<hash>/` on disk. That breaks the issue's missing-pointer best-effort no-op contract and can litter the cache on every failed default append.
- **Proposed resolution**: In `append_breadcrumb`, open the clone directory only with `_open_verified_dir(progress_clone_dir(repo_root))`; on `OSError`, return `False` without creating directories. After a verified fd exists, read `current` via `_read_active_run_id_from_dirfd`, then open the run subdir with `_open_or_create_subdir` and append with `_append_line_in_dir`. Drop `_ensure_directory_fd` from the default-writer shape; keep `_ensure_directory_fd` limited to `activate_run` and `append_breadcrumb_for_run`. Add an assertion in the missing-`current` acceptance test that `progress_clone_dir(repo)` does not exist after a failed default append.

---LARCH-REJECTED-END---
