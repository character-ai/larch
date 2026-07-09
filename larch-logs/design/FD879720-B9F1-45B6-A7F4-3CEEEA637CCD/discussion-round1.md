## Decision 1: Scope boundary (dormant primitives only)
- **Question**: Does piece 1 of 4 add primitives only, or also wire the live path?
- **Resolution**: Primitives only. Add clone-dir/current/run-log helpers, run-id validation, `activate_run`, `progress note --run-id`, `progress activate`, and cleanup of run dirs plus legacy flat logs. Do NOT call `activate_run` from `/design` or `/implement` Step 0. Do NOT make `append_breadcrumb`, writers, or the statusline reader follow the `current` pointer. Live wiring is pieces 2-4.
- **Source**: user

## Decision 2: run-id validation strictness
- **Question**: How strict should run-id validation be?
- **Resolution**: Strict allowlist. Accept only a conservative charset (`[A-Za-z0-9._-]`). Reject empty, `.`, `..`, path separators, and control characters. Refuse symlinked run dirs, pointer, and log via `assert_no_symlink_path_or_ancestors` plus `O_NOFOLLOW`.
- **Source**: user

## Decision 3: Byte-stable existing behavior (hard constraint)
- **Question**: What must not change?
- **Resolution**: Keep `progress_path`, default `append_breadcrumb`, and the statusline reader byte-for-byte unchanged. Existing flat progress and statusline tests must still pass unchanged.
- **Source**: feature description

## Decision 4: In-scope files
- **Question**: Which files may this piece touch?
- **Resolution**: `python/larch/report/progress_file.py`, `python/larch/cli.py`, and `python/tests/report/test_progress_statusline.py`. No skill Step 0 files. Docs stay unchanged because behavior does not change yet.
- **Source**: feature description
