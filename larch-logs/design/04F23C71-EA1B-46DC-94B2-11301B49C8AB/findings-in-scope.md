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

### FINDING_3: Missing ship test for persist-false with readable drop marker
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: No test covers ship returning PR drop text when `maybe_persist` is write-onced out but `DROPPED_NOTE_ARTIFACT` remains readable. Planned tests cover pin-failure persist, compose-then-invalidate integration, and `clear_dropped_note_notice` unlink failure on `write_implement_note`, but not `_pin_and_load_guidelines_note` after successful pin plus failed marker clear plus `note_fingerprint_stale` where `maybe_persist` returns False yet the artifact is readable. Green tests can miss the PR-body regression in FINDING_1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a ship test: pre-seed DROPPED_NOTE_ARTIFACT, pin consumable note, force note_fingerprint_stale, mock maybe_persist to return False (or rely on write-once), assert _pin_and_load_guidelines_note returns the drop notice text for compose_pr_body.

### FINDING_4: Stale-note cleanup can be skipped by earlier fallback branches
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The stale-note cleanup branch can be skipped when an earlier staged-present or marker-return fallback runs first. If a failed pin hits a stale durable note while `staged_present` is true, or `final_report` sees a pre-existing drop marker while stale durable artifacts still exist, the plan can return the notice before `invalidate_implement_note` runs. That leaves old guideline files on disk and makes drop-notice behavior depend on branch order instead of one ordered cleanup path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the stale-note branch take precedence over the staged-only or marker-return fallback in both helpers, or merge them into one ordered decision tree that persists the notice, invalidates once, then returns.

### FINDING_5: Final-report invalidation lacks OSError containment after persist
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Planned stale/live guideline branches in `_architectural_guidelines_section` persist a drop marker then call `invalidate_implement_note` without OSError containment. Ship paths wrap invalidation in try/except and log warnings (`_invalidate_guidelines_note` at `ship.py:501-504`; the plan preserves that). Planned `final_report._architectural_guidelines_section` paths add persist-then-invalidate but still call `invalidate_implement_note` bare (as today at `final_report.py:173`). If invalidation raises after `persist_dropped_note_notice` / `maybe_persist_dropped_note_before_invalidate` succeeds, `write_final_report` catches the exception at `final_report.py:587-591` and aborts before `read_dropped_note_notice`, so `summary-final.md` stays empty even though `DROPPED_NOTE_ARTIFACT` holds the acceptance-required notice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Wrap `invalidate_implement_note` in the final-report guideline branches with try/except `OSError` (log and continue, matching ship). After a successful persist return, read `read_dropped_note_notice` and return the formatted drop section even when invalidation fails.

### FINDING_6: Final-report live drop paths omit `head_sha` guard
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Planned live drop-notice paths in `_architectural_guidelines_section` omit a `head_sha` guard while ship already returns early when `head_sha` is empty. The plan gates drop emission in `_pin_and_load_guidelines_note` on non-empty `head_sha` (edge case line 192) but still lets final-report live branches persist and return a HEAD-drift notice when `_current_head_sha()` is empty yet staged artifacts remain. That revives round-1 FINDING_3: operators can see a drift explanation when HEAD is unknown instead of the current empty result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Before any live persist/return branch (lines 100-105), require non-empty `head_sha`; keep the early `read_dropped_note_notice` path so a ship-persisted artifact can still render when HEAD cannot be resolved.

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:187-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice compose_pr_body regression duplicates existing placement coverage. Scenario: test_pr_body.py already asserts architectural_guidelines_note renders under ## Architectural guidelines and precedes ## Code Flow Diagram (lines 1125-1128). Adding another compose test for static drop text adds churn without guarding a new failure mode.
- **Proposed resolution**: Drop the planned test_pr_body.py addition; rely on ship and final_report tests that assert the actual drop-notice string end-to-end.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:185-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice `compose_pr_body` regression duplicates existing architectural-guidelines placement coverage. Scenario: `test_compose_pr_body_includes_guideline_note_before_mermaid` already asserts any non-empty `architectural_guidelines_note` lands under `## Architectural guidelines` before the Mermaid section; a second test differing only in static drop-notice wording adds churn without new contract signal
- **Proposed resolution**: Drop the `### UPDATED: python/test_pr_body.py` bullet; keep existing placement and redaction tests unchanged

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:185-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice `compose_pr_body` test duplicates existing placement coverage. Scenario: `python/test_pr_body.py:1117-1128` already asserts a non-empty `architectural_guidelines_note` renders under `## Architectural guidelines` with ordering vs `## Code Flow Diagram`. A second test that passes the static drop-notice string exercises the same compose path and adds churn without new failure detection.
- **Proposed resolution**: Skip the `test_pr_body.py` addition unless `compose_pr_body` changes; rely on `test_ship.py` and `test_final_report.py` integration coverage for drop-notice delivery.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_pr_body.py:185-188
- **Concern**: [SCOPE-REDUCTION] Planned drop-notice `compose_pr_body` regression duplicates existing guideline placement coverage. Scenario: `test_compose_pr_body_includes_guideline_note_before_mermaid` (lines 1121-1128) already asserts arbitrary `architectural_guidelines_note` text is rendered under `## Architectural guidelines` before Mermaid. A second test differing only by the static drop-notice string adds no new contract signal for this bugfix.
- **Proposed resolution**: Drop the planned `test_pr_body.py` addition; rely on existing placement/redaction tests plus ship/final_report integration coverage.
