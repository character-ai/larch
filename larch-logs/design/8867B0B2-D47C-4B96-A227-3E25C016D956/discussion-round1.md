## Decision 1: SessionStart reset trigger scope
- **Question**: When should larch wipe the leftover clone-scoped `current` progress pointer so a stale breadcrumb does not render at Claude session start?
- **Resolution**: Wipe the `current` pointer only on SessionStart `source` values `startup` and `clear` (genuinely fresh sessions). Skip the wipe on `resume` and `compact` because a larch run can be mid-flight then and clearing the pointer would silently stop its breadcrumbs. Additionally, skip the wipe whenever a live larch bgjob exists for the clone (protect concurrent/background runs), reusing the same liveness signal the statusline renderer already trusts.
- **Source**: user

## Decision 2: Removal scope (hard constraint)
- **Question**: What must the reset remove, and what must it leave alone?
- **Resolution**: Remove only the clone-scoped `current` pointer file so the statusline renders empty until the next `progress activate`. Do NOT delete run directories or `breadcrumbs.log` files (age-based `cleanup_old_progress_files` retention owns that). Do NOT change `activate_run`, `append_breadcrumb`, `progress note --run-id`, cleanup/retention, or the renderer's staleness math. Preserve the existing symlink-refusal / fd-anchored safety posture used throughout `progress_file.py`.
- **Source**: codebase + user requirements (issue #6768: "no larch log at all when claude starts"; "first larch log entry should be the new run's first breadcrumb")
