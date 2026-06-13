### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/write-final-report.md:105-108
- **Concern**: [SCOPE-REDUCTION] Stale `--no-gantt` / plain-text progress contract after deliverable #3. Scenario: Deliverable #3 adds ASCII timing charts to `p` / `progress`, but the plan only swaps Mermaid→ASCII in final-report prose and still leaves `write-final-report.md` saying `--no-gantt` is reserved so live progress stays plain text. Progress will call the shell renderer with `--no-gantt` and append charts separately; undocumented two-path wiring invites a later “simplify” change that drops Python charts or removes `--no-gantt` and double-renders.
- **Proposed resolution**: Revise `write-final-report.md` (and matching `render-final-summary.md` / `render-review-phase-detail.md` flag docs) to state: final callers omit `--no-gantt`; progress calls the shell with `--no-gantt` for table-only output and appends ASCII charts via `gantt.render_gantt` in `progress_report.py`.

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/progress_report.py:267-281
- **Concern**: [SCOPE-REDUCTION] Plan adds a large progress-only ledger→row pipeline duplicating scripts/render-review-phase-detail.sh awk overlap windowing sort cap and label mapping. Scenario: Progress and final-report charts can diverge when one path is updated or the 13-column parser drifts; violates the issue no-duplication goal for timing semantics
- **Proposed resolution**: Add one public timing-ledger row builder in python/timing.py (thin wrapper over existing _parse_rows plus overlap clamp sort cap) and call it from progress_report; keep shell awk or optionally the same CLI later

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:375-395
- **Concern**: [SCOPE-REDUCTION] Plan reimplements timing-ledger windowing/labeling in progress_report.py while _call_render_phase_detail_script already passes explicit timing_ledger and rounds_root with --no-gantt only to suppress charts. Scenario: Duplicating shell awk logic in Python risks progress vs final-report chart drift (overlap/sort/cap/window rules) and adds ~200+ lines beyond python/gantt.py + shell CLI wiring
- **Proposed resolution**: Prefer dropping --no-gantt once render-review-phase-detail.sh emits ASCII (single subprocess, same extraction path); if subprocess timeout is a concern raise/remove the 6s cap instead of re-parsing the ledger in Python
