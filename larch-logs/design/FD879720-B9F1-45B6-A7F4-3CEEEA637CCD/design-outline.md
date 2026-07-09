## Proposed Design Outline

### Goals
- Add dormant run-scoped primitives to `progress_file.py`: clone-dir, `current` pointer, and run-log path helpers, strict run-id validation, and atomic `activate_run`.
- Add CLI surface: `progress activate` and a `--run-id` override on `progress note` for pointer-independent explicit-run appends.
- Extend cleanup to reap aged run-id subdirectories alongside legacy flat `<clone-hash>.log` files.

### Non-goals
- No wiring of `activate_run` into `/design` or `/implement` Step 0.
- No change to `append_breadcrumb`, `progress_path`, writers, or the statusline reader; they stay byte-for-byte on the flat log.
- No `--run-id` plumbing through review or ship call sites. No docs changes (behavior is unchanged).

### Approach sketch
- New layout target: `~/.cache/larch/progress/<clone-hash>/<run-id>/breadcrumbs.log`; pointer at `<clone-hash>/current`.
- Reuse the existing sha256[:16] clone hash and `consumer_repo_root`; reuse `assert_no_symlink_path_or_ancestors` + `O_NOFOLLOW` for symlink safety.
- `activate_run` writes the pointer atomically (temp file in the clone dir, then `os.replace`).
- Explicit-run append composes clone-dir + run-log helpers; it never reads or writes `current`.
- CLI `progress activate` fails loud on invalid run-id; the append path stays best-effort (returns bool), preserving the `append_breadcrumb` contract.

### Surfaces in scope
- `python/larch/report/progress_file.py`
- `python/larch/cli.py` (progress subcommand registration)
- `python/tests/report/test_progress_statusline.py`

### Open questions
- None. Concurrency of `current` across overlapping runs is deferred with the Step-0 wiring in pieces 2-4.
