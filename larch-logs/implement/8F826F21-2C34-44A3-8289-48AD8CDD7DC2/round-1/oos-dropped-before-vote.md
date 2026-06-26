### OOS_1: [OUT_OF_SCOPE] `review_pipeline.py` dispatch-voters still use archetype timing labels
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-timing-schema-compat-output.txt
- **Severity**: important
- **Concern**: Secondary plan issue, not in this diff: success-path `dispatch-voters` timing rows still use archetype labels (`codex/correctness`, `codex/edge-cases`) instead of voter-slot labels. Retry rows can look disconnected from aggregator rows even with correct per-attempt windows. No labeling changes in this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No substantive fix direction beyond "address the concern" in source outputs.)

### OOS_2: [OUT_OF_SCOPE] Phase-detail table window policy predates branch (Gantt-only scope)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_phase_round_from_meta` still derives Review Phase Detail **Time** and **Cost** from `_timing_round_windows` (`min`/`max` across all `v1 round` rows for a round). After stall recovery the table can show a session-spanning duration even when Gantt splits per attempt. This predates the branch and matches the plan's Gantt-only scope; fixing it would need a separate table-window policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No substantive fix direction beyond "address the concern" in source output.)

### OOS_3: [OUT_OF_SCOPE] Pre-upgrade legacy stall rows expected to collapse (backward-compat tradeoff)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Ledgers with two pre-upgrade stall rows (both trailing `-`, no attempt digit) still collapse into one attempt-1 window. Only post-fix `record_round` writes get distinct attempt indices. Expected backward-compat tradeoff, not a regression for new runs. `test_render_phase_detail_token_ledger_dual_window` should remain valid because design+implement rows on the same round number still merge into a single attempt-1 window.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No substantive fix direction beyond "address the concern" in source output.)

### OOS_4: [OUT_OF_SCOPE] `TimingReport` / timing CLI still ignore attempt column
- **Reviewer(s)**: dyn-dyn-timing-schema-compat-output.txt
- **Severity**: latent
- **Concern**: `TimingReport` / `_parse_rows` still ignore column 12 on `v1 round` rows, and `_rounds_for` deduplicates by `round_n` only (last row wins). Multi-attempt sessions misrepresent round timing in the timing CLI/JSON report; the new attempt column is unused there. Behavior unchanged from pre-branch last-wins semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No substantive fix direction beyond "address the concern" in source output.)

### OOS_5: [OUT_OF_SCOPE] Dual-skill ledger table vs Gantt skill-filter asymmetry (pre-existing footgun)
- **Reviewer(s)**: dyn-dyn-timing-schema-compat-output.txt
- **Severity**: latent
- **Concern**: `_phase_round_from_meta` uses `skill_filtered=True` for table windows while `_render_phase_gantt` calls `_timing_round_attempt_windows` without a skill filter (same as old `gantt_window` `skill_filtered=False`). Shared ledgers with both `design` and `implement` round rows can produce implement Gantt windows that do not match implement-only table timing. Predates the branch but remains a footgun if dual-skill ledgers appear in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No substantive fix direction beyond "address the concern" in source output.)
