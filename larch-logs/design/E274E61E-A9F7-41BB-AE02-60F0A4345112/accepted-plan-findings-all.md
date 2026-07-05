### FINDING_1: Manifest-only reconciliation still drops Outcome
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Final Report Contract
- **Severity**: major
- **Concern**: The stalled-summary reconciliation path rewrites the heading but deletes the `Outcome` bullet, and its safety check only looks for lowercase `stalled`, so recovered summaries can still miss the mandatory `DONE` display or let `STALLED` residue through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In reconcile_stalled_summary_from_manifest, replace del lines[outcome_idx] with rewriting that line to - **Outcome**: DONE (reuse _map_outcome_display from pr_body.py). Extend the post-rewrite guard to reject stalled and STALLED residue. Update test_run_logs.py reconciliation success cases to assert - **Outcome**: DONE, not only absence of stalled.
  - From Cursor-Innovation: In reconcile_stalled_summary_from_manifest, rewrite the matched Outcome line to `- **Outcome**: DONE` (reuse `_map_outcome_display("merged", "implement")` or equivalent) instead of deleting it; extend the line-586 guard to reject any remaining stalled/STALLED Outcome bullet case-insensitively. Update `python/tests/report/test_run_logs.py` reconciliation cases to assert `- **Outcome**: DONE` after a successful repair, not merely absence of `stalled`.
  - From Cursor-Pragmatic: Extend the post-rewrite guard to reject both `stalled` and `STALLED` (same regex/alternation as the matcher), or delete/replace the outcome line via the mapped display (`DONE`) instead of only checking lowercase `stalled`.
  - From Cursor-Requirements: In `reconcile_stalled_summary_from_manifest`, replace the deleted line with `- **Outcome**: {display}` using the same mapper as `render_run_summary` (import `pr_body._map_outcome_display` or a shared helper), e.g. `DONE` for `merged`. Update the post-rewrite guard to reject leftover `stalled`/`STALLED` display values. Extend `python/tests/report/test_run_logs.py` reconciliation cases to assert `- **Outcome**: DONE` after a successful rewrite.
  - From Cursor-dyn-Final Report Contract: Replace the delete with a rewrite to `- **Outcome**: {_map_outcome_display(recovered_outcome)}` (DONE for `merged`); extend reconciliation tests to assert DONE on success recovery


### FINDING_2: Degraded /design fallback skips shared Outcome mapping
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-dyn-Final Report Contract, Codex-dyn-Final Report Contract
- **Severity**: major
- **Concern**: The degraded `/design` fallback still hand-writes the summary instead of using the shared outcome-display mapper, so a renderer failure can publish raw `approved`/`stalled` values and diverge from the normal `DONE`/`STALLED` contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Call the same _map_outcome_display helper (or render_run_summary) in the fallback block so approved and stalled use DONE and STALLED consistently.
  - From Codex-Arch: Apply the same mapper in the fallback writer so `/design` matches `/implement` on DONE/STALLED display.
  - From Cursor-Innovation: Apply the same outcome-display mapping in the fallback block, or route the fallback through the shared summary helper before writing the body.
  - From Codex-Innovation: Mirror the new display mapper in the fallback block, or route the fallback through the shared renderer helper so the degraded path emits the same `Outcome` bullet contract
  - From Codex-Pragmatic: Update the fallback to reuse the same Outcome display mapping, emit `- **Outcome**:` first, and add a regression test for the degraded `/design` path.
  - From Cursor-dyn-Final Report Contract: Add `### UPDATED: python/larch/design/design_summary.py` to reuse `_map_outcome_display` (or a thin shared helper) in the fallback writer
  - From Codex-dyn-Final Report Contract: Apply the same outcome-display mapping in the fallback block, and extend `python/tests/design/test_design_summary.py:461-478` to assert the fallback body uses the mapped `Outcome` line.


### FINDING_3: Report tests still assert lowercase stalled
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The report tests still encode stale lowercase `stalled` expectations for both the live render and reconciliation paths, so they won't validate the new `STALLED`/`DONE` display contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add this test to the plan's `test_run_logs.py` work: expect `- **Outcome**: STALLED` on the stall write, and on recovery expect `- **Outcome**: DONE` (or at minimum assert `stalled`/`STALLED` absent and `DONE` present).
  - From Codex-Requirements: Assert STALLED in the live render path and keep a separate lowercase legacy fixture only for reconciliation coverage.


### FINDING_4: Conditional Outcome append can duplicate the new bullet
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The plan adds an unconditional Outcome bullet but never removes the existing conditional Outcome append, so several non-success paths can emit duplicate or conflicting Outcome bullets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the pr_body.py step, remove the conditional Outcome block entirely and keep one unconditional first bullet: - **Outcome**: {_map_outcome_display(outcome)}


### FINDING_5: Flush test still only guards lowercase stalled
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The flush pre-recovery test still asserts against lowercase stalled only, so it can miss cases where the rendered outcome bullet becomes STALLED or fails to become DONE after recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit plan step for this test: stall phase expects `- **Outcome**: STALLED`; recovery phase expects `- **Outcome**: DONE` (not only absence of lowercase `stalled`)
  - From Cursor-Requirements: In the same flush test, assert `- **Outcome**: DONE` after recovery and reject both `stalled` and `STALLED` residue in the Outcome bullet


