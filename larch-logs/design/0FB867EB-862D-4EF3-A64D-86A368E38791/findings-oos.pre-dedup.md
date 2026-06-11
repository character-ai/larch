### OOS_1:
- **Description**: `_current_round_dir` settlement marker is implement-specific. Scenario: Design `plan-review/round-N/` never writes `review-and-fix.env`, so every round stays in the unsettled set and the helper always picks the highest `round-N`. That matches the live reviewer-count path today, but it also inherits the between-round “round N in progress” wording when a round has finished and the next directory does not exist yet (same class as implement Step 5).
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/progress_report.py:280-285
- **Phase**: design

### OOS_1:
- **Description**: [OUT_OF_SCOPE] Rich header tracks plan-review-slots only, not plan-voter-slots. Scenario: During the voting sub-phase the latest artifact is often plan-voter-slots.ndjson.output-files while the timing label stays design Step 3 — plan review. The report can show N/N reviewers returned and omit voter progress, matching the user's shallow hook snapshot.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/progress_report.py (planned _render_design_plan_review)
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] Rich Step 3 report replaces generic output and drops last artifact. Scenario: When _render_design_plan_review returns non-empty, _render_design skips _render_generic, so the last artifact line disappears during Step 3 even though it can signal the active sub-step (e.g. voter sidecar).
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: python/progress_report.py (planned _render_design)
- **Phase**: design

### OOS_1:
- **Description**: [OUT_OF_SCOPE] Some listed edge cases lack matching regression tests. Scenario: The plan asks to cover every Edge Cases item, but the proposed test list does not explicitly cover round-local manifest stale only by round-start-s, unreadable root manifest, duplicate output paths, both round start and Step 3 start absent, or render-review-phase-detail.sh absent/non-zero.
- **Reviewer**: Codex-dyn-freshness-floor
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:146-159,193-208; python/test_progress_report.py
- **Phase**: design

