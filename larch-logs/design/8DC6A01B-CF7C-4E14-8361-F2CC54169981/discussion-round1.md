## Decision 1: render-run-summary.sh and compose-pr-summary.sh status

- **Question**: Are these scripts already migrated to Python, or are they still live consumers?
- **Resolution**: Both are already ported. `pr_body.py::render_run_summary` is the in-process implementation called by `write_final_report`. `pr_body.py::compose_pr_summary_main` is the in-process implementation called from `/implement` SKILL.md via `python3 cli.py pr compose-summary`. The bash scripts exist but are not called by any live non-test consumer. This PR retires them: delete bash files, delete harnesses, add to `migrated-scripts.tsv`.
- **Source**: codebase

## Decision 2: write-design-round-meta.sh module placement

- **Question**: Which Python module should `write-design-round-meta.sh` port into?
- **Resolution**: Port into `progress_report.py` (issue names it as a target) with CLI verb `progress write-design-round-meta --round-dir DIR`. The caller `review-design-step3-loop.sh` uses an env override `WRITE_DESIGN_ROUND_META_SH` that allows the call to be redirected to a thin delegation wrapper.
- **Source**: codebase

## Decision 3: render-findings-view.sh module placement

- **Question**: Which Python module should `render-findings-view.sh` port into?
- **Resolution**: Port into `rendering.py` (issue names it as a target) with CLI verb `render findings-view RUN_DIR [VIEW]`. The script is operator-only; no live callers need repointing.
- **Source**: codebase

## Decision 4: gc-run-logs.sh module placement

- **Question**: New module or extend existing?
- **Resolution**: New `python/gc_run_logs.py` module. CLI verb `gc-run-logs run` with flags `--older-than DAYS`, `--delete`, `--dry-run`. SKILL.md updated to call `python3 cli.py gc-run-logs run`.
- **Source**: codebase

## Decision 5: status.sh module placement

- **Question**: New module or extend existing agent.py?
- **Resolution**: Port into `agent.py` — the script only calls `plugin read-version`, `agent check-reviewers`, and `agent degraded-tools-gate`, all already in `agent.py`. Add `status_check_main` to `agent.py` with CLI verb `status check`. SKILL.md updated to call `python3 cli.py status check`.
- **Source**: codebase

## Decision 6: render-review-phase-detail.sh Gantt scope

- **Question**: Include Gantt portion despite in-flight #4546 overlap?
- **Resolution**: Include fully (operator confirmed). Port the complete body including Gantt chart generation into `progress_report.py`. The `review_phase_detail.py::_invoke_renderer` subprocess call becomes an in-process Python call. A new CLI verb `progress render-phase-detail` is added.
- **Source**: operator decision (Step 1c)
