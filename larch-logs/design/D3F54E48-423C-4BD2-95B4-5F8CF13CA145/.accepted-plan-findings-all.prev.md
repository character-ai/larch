### FINDING_1: `/review` flat layout omits timing-ledger binding for apply rows
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan adds Cursor apply timing via `run-external-agent --timing-task-kind`, but does not bind the session ledger for the flat `/review` `apply-findings` layout. When `/review` calls `apply_findings_with_coder(..., review_tmpdir, ...)` with `round_dir == review_tmpdir` (not `round-<N>/`), timing recording resolves the ledger from `LARCH_TIMING_LEDGER` / `REVIEW_TMPDIR` env. `apply_findings` only rehydrates session env and does not export `REVIEW_TMPDIR` or fall back to `review_tmpdir/timing-ledger.tsv`. If the Skill subprocess lacks a ledger key, the new apply row is never written and `/review` Gantt charts stay unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `_run_coder_cursor`, resolve the ledger before launch: use `round_dir / "timing-ledger.tsv"` when `round_dir.name` does not match `round-<N>`, else `round_dir.parent / "timing-ledger.tsv"`; pass it via `--ledger` on `timing record-vendor-task` or set `LARCH_TIMING_LEDGER` in the subprocess env. Add an offline `apply_findings` test that stubs the coder and asserts the ledger path when session env omits `LARCH_TIMING_LEDGER`.


### FINDING_2: `/design` plan-revise apply labels target wrong output files
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan labels `/design` plan-autofix apply rows for `codex.log`/`cursor.log`, but `plan revise-waterfall` emits `codex-output.txt`/`cursor-output.txt` (tier-output files). Accepted-finding apply rows from plan revise-waterfall can keep old `codex-plan-autofix` or `cursor-plan-autofix` technical labels instead of the intended `codex/apply` or `cursor/apply` display labels. Tests may pass against the separate validator-autofix `codex.log`/`cursor.log` path rather than the actual review-apply path, so the required design apply path is not pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Label codex-plan-autofix and cursor-plan-autofix apply rows for the actual revise-waterfall outputs, or make the renderer/test fixture explicitly cover codex-output.txt and cursor-output.txt from plan revise-waterfall; avoid treating unrelated validator-autofix rows as the only design apply coverage
  - From Codex-Requirements: Apply the label special case to the actual revise-waterfall outputs or to the plan-autofix task kinds, and cover that fixture in the renderer test


### FINDING_3: Chart window still follows displayed task span, not round duration
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan keeps chart axes tied to the displayed task span, despite the approved goal that the Gantt window match the round duration. When post-apply verification remains excluded, the chart can still end before the round-meta end and preserve an unexplained tail gap between the last charted bar and the round's `type=round` duration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Use the existing round window gw_start/gw_end for the rendered window and title while keeping CI rows filtered


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agents.py:1604-1680; python/review_and_fix.py:1250-1286
- **Concern**: [SCOPE-REDUCTION] Plan adds a new generic agent run-external-agent timing flag to solve one Cursor apply caller. Scenario: This expands a public launcher CLI, parser validation, and python/test_agents.py even though the feature only needs a cursor-review-fix vendor row for _run_coder_cursor. The generic reusable surface is not materially required for the Gantt fix.
- **Proposed resolution**: Drop python/agents.py and python/test_agents.py from the plan. In _run_coder_cursor, capture start/end around the existing _run call and invoke python3 cli.py timing record-vendor-task with vendor cursor, task-kind cursor-review-fix, output coder-cursor.log, exit-code result.returncode, and complete/signal status; ignore timing-record failures like existing timing callers.


### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agents.py:1604-1680
- **Concern**: [SCOPE-REDUCTION] Plan extends generic agent run-external-agent with optional --timing-task-kind for a single /implement /review apply callsite. Scenario: Adds agents.py parsing, recording, and test_agents.py coverage for one consumer while plan_quality.py already records cursor apply timing locally via timing record-vendor-task in _dispatch_vendor_fix
- **Proposed resolution**: Record cursor-review-fix in _run_coder_cursor with a local timing record-vendor-task call (mirror python/plan_quality.py:1819-1843) and limit renderer/progress label changes to review-fix and plan-autofix kinds


### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agents.py:1604-1680; python/review_and_fix.py:1250-1278
- **Concern**: [SCOPE-REDUCTION] Plan adds generic timing support to agent run-external-agent for one Cursor apply caller. Scenario: The feature only needs the Cursor apply coder to emit a vendor row. Broadening a reusable CLI adds parser validation and tests without being required, and exposes timing behavior to unrelated callers.
- **Proposed resolution**: Record cursor-review-fix directly in python/review_and_fix.py around _run_coder_cursor using the existing timing record-vendor-task pathway, similar to python/plan_quality.py:1786-1840. Drop the python/agents.py and python/test_agents.py plan changes.


### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-review-phase-detail.sh:413-421
- **Concern**: [SCOPE-REDUCTION] Apply-label rules key off codex.log/cursor.log but /design plan-review apply writes codex-output.txt/cursor-output.txt. Scenario: Approved outline calls for codex/apply and cursor/apply labels; plan revise-waterfall emits *-plan-autofix rows with *-output.txt basenames (python/plan_quality.py:1464-1470) so /design apply stays codex/codex-plan-autofix per plan carve-out and tests at scripts/test-render-review-phase-detail.sh:164-165
- **Proposed resolution**: Map codex-review-fix/cursor-review-fix and codex-plan-autofix/cursor-plan-autofix kinds to codex/apply and cursor/apply in label_for (and progress_report) by kind alone; drop codex.log/cursor.log basename conditionals and update the two plan-autofix label assertions if needed



### FINDING_1: Harness must expect ledger window span after axis switch
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan omits a harness update for the Gantt title span after switching the chart axis to ledger `gw_start`/`gw_end`. The fixture round row spans 65s (1700000000–1700000065) while the only vendor bar spans 50s; today’s title is `window 0:00-0:50 (50s)` from task min/max. After the planned change, the title becomes `window 0:00-1:05 (65s)` and `assert_contains 'window 0:00-0:50 (50s)'` fails on `make test-harnesses-19`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/implement/scripts/test-write-final-report.sh` with the window assertion updated to `0:00-1:05 (65s)` (or derive expected span from the fixture round row)


### FINDING_2: Plan mislabels Gantt axis source as round-meta window
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan mislabels the chart axis source as “round-meta window”. `round-meta.json` has no start/end timestamps. Gantt windows already come from ledger `type=round` rows via `gantt_rrange` (unfiltered by `--skill`) into `round_windows_file`. Reading `round-meta.json` or skill-filtered round rows would break Test 12 preservation (vendor at 1700000500 needs the 1800s cross-skill window).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Reword Approach and `render-review-phase-detail.md` edits to say “ledger `gantt_rrange` / existing `gw_start`/`gw_end`”; implement only the title/axis change inside the existing `while read gw_rn gw_start gw_end` loop


### FINDING_4: Cursor apply timing record must pass --ledger explicitly
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Cursor apply timing record must pass `--ledger` explicitly, not env alone. `_record_coder_vendor_task` best-effort via env can miss when session `LARCH_TIMING_LEDGER` is empty or points elsewhere; flat `/review` is the binding surface in the issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mirror `record_round_timing`: call `timing record-vendor-task` with `--ledger <resolved>` plus vendor/task_kind/start/end/output fields


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:1250-1316
- **Concern**: [SCOPE-REDUCTION] `_record_coder_vendor_task` should always pass `--ledger <resolved>` to `timing record-vendor-task`, not only set `LARCH_TIMING_LEDGER` in a child env with hedged "when supported" wording.. Scenario: `resolve_timing_ledger_path` honors `--ledger` first; env-only recording is easier to mis-wire in tests or nested sessions, so apply rows can still miss the round ledger the renderer reads.
- **Proposed resolution**: Pin the helper to always append `--ledger` with `_resolve_coder_timing_ledger(round_dir)`; keep env keys as secondary context only (`LARCH_TIMING_SKILL`, `REVIEW_TMPDIR` / `IMPLEMENT_TMPDIR`).



