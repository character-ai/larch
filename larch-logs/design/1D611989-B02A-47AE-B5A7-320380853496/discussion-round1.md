## Decision 1: Concurrent /design and /implement in the same clone
- **Question**: How should piece 4 handle two larch runs (e.g. /design and /implement) sharing one clone, given one `current` pointer and one statusline per clone?
- **Resolution**: Non-issue by hard rule. No two larch skills may EVER run simultaneously in the same clone — one job per clone is a hard larch invariant. Therefore piece 4 needs NO concurrency guard: the last-writer-wins `current` pointer is safe because only one run is ever active per clone. Keep the issue's "writers follow the pointer" design unchanged; do NOT add live-run guarding / pointer-steal protection to `activate_run`. Document the per-run contract on the assumption of one active run per clone.
- **Source**: user

## Scope boundaries (from issue #6686, hard constraints carried forward)
- In scope — 4 firm files ONLY: `python/larch/report/progress_file.py`, `python/larch/report/statusline.py`, `python/tests/report/test_progress_statusline.py`, `docs/progress-reporting.md`.
- Flip the DEFAULT production writer `append_breadcrumb` to require a valid `current` pointer and append into `<clone-hash>/<run-id>/breadcrumbs.log`; return `False` (fail-silent no-op) when the pointer is missing/invalid.
- Flip the statusline reader (`render_statusline` / `_age_suffix`) to follow the `current` pointer to the run-scoped log; render nothing when the pointer / subdir / file is missing; ignore legacy flat `<clone-hash>.log`.
- Preserve fail-silent symlink and corruption behavior; keep file-mtime age and the clone-filtered bgjob liveness check (now run-scoped because prior runs' files are never selected).
- Do NOT touch: `activate_run` semantics, cleanup/retention (already reaps run-id subdirs), or the `progress note --run-id` override — all landed in dependency pieces 1–3.
- Hard constraint: NO run-id plumbing through review/ship call sites. Writers keep their signature and resolve the active run via the pointer.
- Acceptance to satisfy: new run starts empty; older same-clone runs never render; missing/invalid `current` → appends return `False` and statusline empty; legacy flat logs ignored by the reader; active-run mtime drives stale display; symlinked pointer/log ancestors fail silent.
