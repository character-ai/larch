### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_phase_detail.py:63-66
- **Concern**: [SCOPE-REDUCTION] append_review_phase_detail only EOF-appends while Approach requires post-sentinel placement. Scenario: Plan Approach and failure modes require detail after <!-- larch:run-summary v=1 -->. Blind EOF append matches today only when the sentinel is the final line. render_run_summary already supports note_lines after the sentinel (python/pr_body.py:418-420). EOF append can place detail in the wrong position relative to the compact block contract if note_lines or trailing markers are added later.
- **Proposed resolution**: Implement marker-relative splice: find <!-- larch:run-summary v=1 --> and insert one blank line plus detail immediately after that line (or after note_lines if mirroring legacy shell note-block semantics), not unconditional EOF append.

