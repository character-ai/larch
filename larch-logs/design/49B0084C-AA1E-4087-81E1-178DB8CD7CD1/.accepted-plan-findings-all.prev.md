### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:591-606,902-963
- **Concern**: In-flight Gantt is gated only on `_all_round_dirs_inflight`. Scenario: When round 1 has `round-meta.json` and round 2 is active (common in `/implement` Step 5), `_all_round_dirs_inflight` is false, detail renders completed rounds only, and the current round gets no live Gantt despite the outline goal
- **Proposed resolution**: Also render `_render_inflight_gantt` for `_current_round_dir` when that dir lacks `round-meta.json`, appending the chart to the mixed-state header+detail path (keep the all-inflight early return for the no-completed-rounds case)


### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/progress_report.py:303-319,408-413
- **Concern**: Plan mirrors Bash `derive.awk` in `_derive_progress_label` but not Bash `label_for` kind priority. Scenario: Bash `label_for` uses `vendor/kind` for bare `codex-output.txt` / `cursor-output.txt` when derive yields a bare vendor; Python always calls `_derive_progress_label` and maps `codex-output.txt` to `codex/panel`, so progress-report revision/autofix bars stay mislabeled even after `--timing-task-kind` is added
- **Proposed resolution**: Add the same kind-priority rule at the `_progress_vendor_rows` label site (or extend `_derive_progress_label` with an explicit kind parameter path) before falling back to derive


### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:303-319
- **Concern**: `_derive_progress_label` must apply codex-output/cursor-output task-kind overrides before the `codex-`/`cursor-` prefix branch. Scenario: Plan mirrors Bash `label_for` but Python currently maps `codex-output.txt` to `codex/output` via the prefix rule, so even with `--timing-task-kind codex-plan-autofix` revision bars stay mislabeled in progress-report Gantt output
- **Proposed resolution**: In `_derive_progress_label`, special-case `codex-output`/`cursor-output` (or non-empty `task_kind` on those basenames) before the existing prefix loop; add/keep the unit assertion from the plan


### FINDING_6:
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-label-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:591-606,959-963
- **Concern**: In-flight Gantt is only planned for all-in-flight roots. Scenario: A second review round can be running after round 1 has round-meta.json. _all_round_dirs_inflight is false, so the progress report renders completed detail only and omits the current round's in-flight Gantt. Implement flushed-log roots have the same gap.
- **Proposed resolution**: Render the in-flight chart whenever the current round lacks round-meta.json. Append it beside completed detail. Skip _call_render_phase_detail_script only when there are no completed round-meta.json files.


### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/progress_report.py:462-475
- **Concern**: In-flight Gantt gated on all rounds lacking round-meta. Scenario: When round 1 is complete and round 2 is in progress `_all_round_dirs_inflight` is false so `_render_design_plan_review` and `_render_step5` skip `_render_inflight_gantt` and only render completed-round detail; live Gantt never appears for round 2+
- **Proposed resolution**: Gate in-flight rendering on the current round dir missing `round-meta.json` (use `_current_round_dir`) instead of requiring every round dir to be inflight


### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:591-606,902-963
- **Concern**: In-flight Gantt wiring only runs when all round dirs are in-flight. Scenario: After round 1 has round-meta.json, a round 2 live review has no round-meta.json but _all_round_dirs_inflight returns false, so progress shows completed detail and omits the required in-flight chart for the running round
- **Proposed resolution**: Render the in-flight chart whenever the current round_dir lacks round-meta.json, independent of whether prior rounds are completed; append it to the header before or alongside completed detail


### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/review-design-step3-loop.sh:683-738
- **Concern**: Postplan-failed timing uses the current process start instead of the persisted round start on resumed phases. Scenario: In awaiting-postplan-operator or other resumed phases, round_start_s is reset on re-entry, so the new round row can start after the reviewer or autofix vendor rows and the final Gantt still omits those bars
- **Proposed resolution**: Read plan-review/round-N/round-start-s when present for postplan-failed timing records, falling back to round_start_s only when missing; add the timing-stub test to assert the persisted start is used


### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/review-design-step3-loop.sh:573-576,683-735
- **Concern**: F1 postplan-failed timing still uses per-iteration round_start_s instead of the persisted round start. Scenario: After an approval, apply, or operator-required re-entry, line 576 resets round_start_s after earlier reviewer or revision work. The proposed pre-exit timing row can still create a Gantt window that omits plan-revision bars, leaving the stated postplan-failed goal broken.
- **Proposed resolution**: Read plan-review/round-$round_num/round-start-s for terminal timing, with the local value only as fallback. Update the three postplan-failed tests to assert the recorded start equals the persisted round start, not merely a numeric field.


### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:591-606,902-963
- **Concern**: F2 in-flight Gantt wiring is limited to all-rounds-inflight roots. Scenario: The plan returns an in-flight chart only when every round lacks round-meta.json. In a later review round with prior completed rounds, progress reports will still show completed detail only and omit the current in-flight Gantt, despite the requirement to show an in-flight timing Gantt while reviewers are running.
- **Proposed resolution**: Render the current round's in-flight Gantt whenever the current round lacks round-meta.json. Keep skipping the detail script only for the all-in-flight case, but append the current in-flight chart beside completed detail for mixed completed-plus-in-flight roots.


### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-inflight-window
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:603-606
- **Concern**: python/progress_report.py:960-963. Scenario: In-flight Gantt is gated only on `_all_round_dirs_inflight`
- **Proposed resolution**: When an earlier round has `round-meta.json` but the current round does not (typical round 2+), `_all_round_dirs_inflight` is false, `_render_review_detail` runs, and `_render_progress_timing_charts` only charts completed rounds; the live round gets no Gantt despite the goal to show timing while reviewers run Trigger `_render_inflight_gantt` whenever `_current_round_dir(...)` lacks `round-meta.json`, not only when every round dir lacks meta; in mixed state append the chart after detail


### FINDING_13:
- **Reviewer(s)**: Codex-dyn-inflight-window
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:591-606, python/progress_report.py:902-963, python/test_progress_report.py:453-467, python/test_progress_report.py:493-516
- **Concern**: The plan only wires in-flight Gantt rendering for all-in-flight roots. Scenario: The current round can be in flight after round 1 completed. Existing mixed-state paths render only completed detail, so round 2 reviewer timing still lacks the current in-flight Gantt.
- **Proposed resolution**: Update the plan to append a current-round in-flight chart when the selected current round lacks round-meta.json, even if earlier rounds are complete.


### FINDING_14:
- **Reviewer(s)**: Codex-dyn-inflight-window
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:216-223, skills/review-and-fix/scripts/review-implement-step5-loop.sh:240-253, python/legacy_review_shell/dispatch-panel.sh:101-121, python/progress_report.py:626-644
- **Concern**: The implement in-flight window can fall back to round directory mtime because round-start-s is not persisted while reviewers run. Scenario: Step 5 keeps round_start_s local during reviewer execution and only persists it for handoff paths. Reviewer outputs are direct children of the round dir, so directory mtime can advance to a completed vendor output time. The proposed mtime fallback can then exclude that completed row.
- **Proposed resolution**: Use the existing Step 5 timing mark start_s as the in-flight fallback, or persist round-start-s before launching the implement review round. Add the implement test without round-start-s.


### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-label-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-review-phase-detail.sh:392-399
- **Concern**: Planned bare-vendor `derive.awk` tokens block the `vendor/kind` tier in `label_for`. Scenario: After suffix stripping, `codex-output.txt` / `cursor-output.txt` become bare `codex` / `cursor`. `label_for` returns any non-empty derive value before `vendor "/" kind` (line 397). Autofix revision bars stay `codex` / `cursor` instead of `codex/codex-plan-autofix` and `cursor/cursor-plan-autofix` in final-report Gantt even with `--timing-task-kind`
- **Proposed resolution**: After bare-vendor derive rules, add an explicit tier in `label_for`: when derive is a bare vendor token (`codex`, `cursor`, `claude`, `claude_sub`) and `kind` is non-empty and not `-`, return `vendor "/" kind` before returning the bare derive token


### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-postplan-timing
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/review-design-step3-loop.sh:576-576,723-724,735-736
- **Concern**: Postplan-failed timing will use loop-local round_start_s after phase continues reset it. Scenario: The while loop sets round_start_s at every iteration (line 576). Apply/post-apply paths call continue (681, 727), so postplan-failed exits at 723 or 735 record timing with a start time from the latest phase iteration, not the review round start in plan-review/round-N/round-start-s. Revise/postplan vendor rows from earlier iterations can fall outside the recorded round window, so Gantt bars still disappear on terminal postplan-failed runs.
- **Proposed resolution**: Before each postplan-failed step3_loop_record_timing call, read plan-review/round-${round_num}/round-start-s when present and numeric; fall back to round_start_s only if the file is missing.


### FINDING_17:
- **Reviewer(s)**: Codex-dyn-postplan-timing
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/review-design-step3-loop.sh:568-576,683-738; skills/design/scripts/plan-review-loop.sh:488-499; plan.txt:13-21,135-145
- **Concern**: FINDING_1 [correctness] Proposed postplan-failed timing records use the current loop invocation start, not the persisted round start. Scenario: After an operator-required or apply-required resume, round_start_s is reset at loop entry. The new postplan-failed round row can start after reviewer and revision vendor rows, so the final Gantt still clips out the bars this issue is meant to restore. The planned tests only require numeric start and end, so they would not catch the wrong start.
- **Proposed resolution**: Prefer plan-review/round-N/round-start-s when recording the three new postplan-failed timing rows, falling back to round_start_s only when absent. Seed round-start-s in the three timing-stub tests and assert the recorded start equals it.



### FINDING_2: `_render_step5` header-only return blocks in-flight Gantt
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds `_render_inflight_gantt`, but `_render_step5` still returns header-only when `_all_round_dirs_inflight(selected_root)` is true (`progress_report.py:603-604`). On the first in-flight round (every round dir lacks `round-meta.json`), the new chart never renders.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Replace the `_all_round_dirs_inflight(selected_root)` return-header branch with header plus `_render_inflight_gantt` output (and keep skipping `_call_render_phase_detail_script` when no completed meta exists).



