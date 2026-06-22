# Review Round 2

- Mode: `diff`
- 3 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: step18b `.step17-emitted` gate can duplicate Step 16 on green-path Step 17 failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: step18b invokes `step_16_16a` whenever `.step17-emitted` is absent, but that sentinel is also missing after a green-path `step-16-17` when Step 17’s final-report write fails after Step 16/16a already ran. In that case Step 18b re-runs rejected-findings replay and Slack via `step_16_16a` even though Step 16 already succeeded. `skills/implement/scripts/step-18.md` documents `step-16-16a` only for terminal-stall recover-then-report, while code triggers on any missing `.step17-emitted`, so documentation and implementation disagree on non-stall paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Write a `.step16-16a-done` sentinel from `step_16_17`/`step_16_16a` and gate step18b on it, or restrict `step_16_16a` to recover-then-report terminal stalls only.
  - From cursor-specialist-correctness-output.txt: Align implementation and contract with the sentinel gate from finding 1.


### FINDING_4: MAV/coder lint-fail terminal-stall bullets omit ship-pr-state seeding
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: MAV/coder lint-fail terminal-stall bullets skip to Step 18 without explicitly requiring ship-pr-state seeding from the deferred-timing block. The orchestrator may run record-only then jump to Step 18a without durable `STALL_STEP` / `BAIL_REASON` / `BAIL_FAILURE_DETAIL_LOG` keys, weakening stall classification and recovery on paths now routed only through Step 18a.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align MAV/coder bullets with the full deferred-timing block (record-only, seed/key-rewrite `ship-pr-state.sh`, skip to Step 18) or merge into one canonical procedure.


### FINDING_7: Incomplete TSV row can swallow the next valid row in `research_eval.py`
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: In `python/research_eval.py:193-199`, if a reviewer emits row 1 missing `suggested_fix` and row 2 starts with `2\t...`, the parser appends row 2 into row 1’s fix field because the buffer has fewer than 7 tabs. The validator then accepts one corrupted row and drops the real row 2 finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: When a new row prefix appears, always close the current buffer. Let `_split_structured_tsv_row` reject the incomplete row, then start a fresh buffer for the new row. Use continuation joining only for non-row-prefix lines.


