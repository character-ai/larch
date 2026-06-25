### FINDING_1: Ship omits `read_dropped_note_notice` when persist returns False
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Planned ship drop-notice paths return `""` when `persist_dropped_note_notice` or `maybe_persist_dropped_note_before_invalidate` returns False, without falling back to `read_dropped_note_notice`. After a successful pin, `clear_dropped_note_notice` can fail and leave a stale marker; `note_fingerprint_stale` then hits write-once `maybe_persist` (False), invalidates the fresh durable note, and ship returns `""` while a readable `DROPPED_NOTE_ARTIFACT` remains. PR compose can ship with no `## Architectural guidelines` content even though acceptance requires the PR body or final report to explain the drop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After any persist call returns False, fall back to read_dropped_note_notice when non-empty before returning ""; align with final_report ordering. Treat a readable persisted marker as satisfying the only-surface-when-persisted rule (line 20).


### FINDING_2: `note_consumable` early return blocks planned drop-marker path in final report
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan restructures drop handling but does not require removing the combined `if not head_sha or not note_consumable: return ""` guard in `_architectural_guidelines_section`. After compose-pin plus `_invalidate_guidelines_note`, `note_consumable` is false while `DROPPED_NOTE_ARTIFACT` may hold the drop notice; the early return prevents the planned `read_dropped_note_notice` and live-persist branches from running, so `summary-final.md` stays silent and round-3 acceptance still fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Explicitly require replacing the combined if not head_sha or not note_consumable: return "" guard with the ordered flow: consumable non-stale happy path, then read_dropped_note_notice, then live persist branches; only keep a head_sha empty short-circuit if drop-marker reads must also be blocked.
  - From Cursor-Innovation: Replace the combined guard with explicit ordering: run the consumable+non-stale happy path only when `head_sha` and `note_consumable`; then read `DROPPED_NOTE_ARTIFACT` whenever the happy path did not return; only then handle live stale/staged branches. Add a regression test that pre-seeds the drop artifact, forces `note_consumable` false, and asserts the section renders without relying on live staged/durable files


### FINDING_5: Final-report invalidation lacks OSError containment after persist
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Planned stale/live guideline branches in `_architectural_guidelines_section` persist a drop marker then call `invalidate_implement_note` without OSError containment. Ship paths wrap invalidation in try/except and log warnings (`_invalidate_guidelines_note` at `ship.py:501-504`; the plan preserves that). Planned `final_report._architectural_guidelines_section` paths add persist-then-invalidate but still call `invalidate_implement_note` bare (as today at `final_report.py:173`). If invalidation raises after `persist_dropped_note_notice` / `maybe_persist_dropped_note_before_invalidate` succeeds, `write_final_report` catches the exception at `final_report.py:587-591` and aborts before `read_dropped_note_notice`, so `summary-final.md` stays empty even though `DROPPED_NOTE_ARTIFACT` holds the acceptance-required notice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Wrap `invalidate_implement_note` in the final-report guideline branches with try/except `OSError` (log and continue, matching ship). After a successful persist return, read `read_dropped_note_notice` and return the formatted drop section even when invalidation fails.


