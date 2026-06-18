## Proposed Design Outline

### Goals
- Port 8 bash scripts (~2.0k lines) to Python, following the standard sh-to-py recipe.
- Eliminate all remaining bash consumers: cut callers to `python3 cli.py`, delete bash files + harnesses + `.md` siblings.
- Extend `progress_report.py`, `pr_body.py`, `review_and_fix.py`, and `rendering.py` with in-process bodies; add new modules for `gc-run-logs` and `agent status check`.

### Non-goals
- Do not port `write-final-report.sh` (already a thin wrapper).
- Do not change the output format or contract of any ported script.
- Do not refactor callers beyond the consumer cutover required by the recipe.

### Approach sketch
- Port `render-review-phase-detail.sh` body into `progress_report.py`; add `progress render-phase-detail` CLI verb; update `review_phase_detail.py` to call in-process.
- Port `write-design-round-meta.sh` body into `progress_report.py`; add `progress write-design-round-meta` CLI verb; cut `review-design-step3-loop.sh` caller.
- Port `write-implement-round-meta.sh` body into `review_and_fix.py`; replace subprocess call at line 1770 with in-process call.
- Port `render-findings-view.sh` body into `rendering.py`; add `render findings-view` CLI verb.
- Port `gc-run-logs.sh` body into new `python/gc_run_logs.py`; add `gc-run-logs run` CLI verb; update `gc-run-logs/SKILL.md`.
- Port `status.sh` body into `agent.py`; add `status check` CLI verb; update `skills/status/SKILL.md`.
- Retire `render-run-summary.sh` and `compose-pr-summary.sh` (already ported): delete bash + harnesses, add to `migrated-scripts.tsv`.
- Write pytest for all new Python bodies; delete bash harnesses.

### Surfaces in scope
- `python/progress_report.py` — two new functions + CLI verb
- `python/review_and_fix.py` — in-process round-meta write
- `python/rendering.py` — `render findings-view` verb
- `python/pr_body.py` — no new body (already ported); parity test update
- `python/gc_run_logs.py` — new module
- `python/agent.py` — `status check` function + CLI verb
- `python/cli.py` — new verb registrations
- `python/review_phase_detail.py` — switch from subprocess to in-process call
- `python/migrated-scripts.tsv` — 8 new entries
- `skills/gc-run-logs/SKILL.md`, `skills/status/SKILL.md` — consumer cutover
- `skills/design/scripts/review-design-step3-loop.sh` — consumer cutover
- `scripts/` bash scripts + harnesses + `.md` siblings — deleted
- `skills/gc-run-logs/scripts/gc-run-logs.sh` + `.md` — deleted
- `skills/status/scripts/status.sh` (create missing `.md` then retire) — deleted

### Open questions
- None.
