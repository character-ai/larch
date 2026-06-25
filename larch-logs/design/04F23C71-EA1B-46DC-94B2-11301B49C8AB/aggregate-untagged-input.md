### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:507-555
- **Concern**: Ship drop-notice paths omit read_dropped_note_notice fallback when persist returns False. Scenario: The plan requires _pin_and_load_guidelines_note to return drop text only when persist_dropped_note_notice or maybe_persist_dropped_note_before_invalidate returns True (lines 80-84), but final_report may read a pre-existing DROPPED_NOTE_ARTIFACT (lines 37-38). After a successful pin, clear_dropped_note_notice can fail (accepted round-4 fix), leaving a stale marker; note_fingerprint_stale then hits write-once maybe_persist (False), invalidates the fresh durable note, and ship returns "" while a readable marker remains. PR compose can ship with no ## Architectural guidelines content even though acceptance requires the PR body or final report to explain the drop.
- **Proposed resolution**: After any persist call returns False, fall back to read_dropped_note_notice when non-empty before returning ""; align with final_report ordering. Treat a readable persisted marker as satisfying the only-surface-when-persisted rule (line 20).

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/final_report.py:162-185
- **Concern**: Plan restructures drop handling but does not require removing the note_consumable early return. Scenario: _architectural_guidelines_section still returns immediately when not note_consumable (lines 164-165). After compose-pin plus _invalidate_guidelines_note, note_consumable is false while DROPPED_NOTE_ARTIFACT may hold the drop notice; the early return prevents the planned read_dropped_note_notice and live-persist branches (plan lines 97-105) from running, so summary-final.md stays silent and round-3 acceptance still fails.
- **Proposed resolution**: Explicitly require replacing the combined if not head_sha or not note_consumable: return "" guard with the ordered flow: consumable non-stale happy path, then read_dropped_note_notice, then live persist branches; only keep a head_sha empty short-circuit if drop-marker reads must also be blocked.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/test_ship.py:137-168
- **Concern**: No test that ship returns PR drop text when maybe_persist is write-onced out but marker remains. Scenario: Planned tests cover pin failure persist, compose-then-invalidate integration, and clear_dropped_note_notice unlink failure on write_implement_note, but not _pin_and_load_guidelines_note after successful pin plus failed marker clear plus note_fingerprint_stale where maybe_persist returns False yet DROPPED_NOTE_ARTIFACT is readable. Green tests can miss the PR-body regression in finding 1.
- **Proposed resolution**: Add a ship test: pre-seed DROPPED_NOTE_ARTIFACT, pin consumable note, force note_fingerprint_stale, mock maybe_persist to return False (or rely on write-once), assert _pin_and_load_guidelines_note returns the drop notice text for compose_pr_body.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:507-542; python/final_report.py:162-185
- **Concern**: 1. The stale-note cleanup branch can be skipped by the earlier staged-present or marker-return fallback.. Scenario: If a failed pin hits a stale durable note while staged_present is true, or final_report sees a pre-existing drop marker while stale durable artifacts still exist, the plan can return the notice before invalidate_implement_note runs. That leaves old guideline files on disk and makes the new drop-notice behavior depend on branch order instead of one ordered cleanup path.
- **Proposed resolution**: Make the stale-note branch take precedence over the staged-only or marker-return fallback in both helpers, or merge them into one ordered decision tree that persists the notice, invalidates once, then returns.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/final_report.py:162-165
- **Concern**: [Prior FINDING_1 incomplete] Plan adds `read_dropped_note_notice` but never requires removing today's combined `if not head_sha or not note_consumable: return ""` gate. Scenario: After ship persists `DROPPED_NOTE_ARTIFACT`, Step 17 hits the early return whenever `note_consumable` is false (the primary pin-failure / post-invalidate case) and never reaches the new drop-marker branch, so `summary-final.md` stays silent despite the fix
- **Proposed resolution**: Replace the combined guard with explicit ordering: run the consumable+non-stale happy path only when `head_sha` and `note_consumable`; then read `DROPPED_NOTE_ARTIFACT` whenever the happy path did not return; only then handle live stale/staged branches. Add a regression test that pre-seeds the drop artifact, forces `note_consumable` false, and asserts the section renders without relying on live staged/durable files

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/final_report.py:162-185
- **Concern**: Planned stale/live guideline branches persist a drop marker then call invalidate_implement_note without OSError containment. Scenario: Ship paths wrap invalidation in try/except and log warnings (`_invalidate_guidelines_note` at `ship.py:501-504`; the plan preserves that). Planned `final_report._architectural_guidelines_section` paths add persist-then-invalidate but still call `invalidate_implement_note` bare (as today at `final_report.py:173`). If invalidation raises after `persist_dropped_note_notice` / `maybe_persist_dropped_note_before_invalidate` succeeds, `write_final_report` catches the exception at `final_report.py:587-591` and aborts before `read_dropped_note_notice`, so `summary-final.md` stays empty even though `DROPPED_NOTE_ARTIFACT` holds the acceptance-required notice.
- **Proposed resolution**: Wrap `invalidate_implement_note` in the final-report guideline branches with try/except `OSError` (log and continue, matching ship). After a successful persist return, read `read_dropped_note_notice` and return the formatted drop section even when invalidation fails.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/final_report.py:162-185
- **Concern**: Planned live drop-notice paths in `_architectural_guidelines_section` omit a `head_sha` guard while ship already returns early when `head_sha` is empty. Scenario: The plan gates drop emission in `_pin_and_load_guidelines_note` on non-empty `head_sha` (edge case line 192) but still lets final-report live branches persist and return a HEAD-drift notice when `_current_head_sha()` is empty yet staged artifacts remain. That revives round-1 FINDING_3: operators can see a drift explanation when HEAD is unknown instead of the current empty result.
- **Proposed resolution**: Before any live persist/return branch (lines 100-105), require non-empty `head_sha`; keep the early `read_dropped_note_notice` path so a ship-persisted artifact can still render when HEAD cannot be resolved.
