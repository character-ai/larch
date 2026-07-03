# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Review transcripts are excluded from heatmap coverage without a manifest
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-transcript-flow
- **Severity**: important
- **Concern**: Standalone `/review` runs can commit `session-transcript.jsonl`, but `measure_references_heatmap()` only counts run directories that `run_log_corpus.run_dirs()` accepts, and that walker currently requires a manifest with a numeric `issue_number`. As a result, committed review transcripts are skipped and review coverage does not accrue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-transcript-flow: Before review `run-log commit`, initialize or update an accepted `manifest.json` (for example via `run-log init` with a review-appropriate `issue_number`, or a review-specific manifest writer), or extend coverage counting to include review transcript dirs that pass `safe_transcript_path()` without requiring implement/design-style manifests.


### FINDING_3: Step 18 should not recapture transcripts after Step 7a has already captured them
- **Reviewer(s)**: dyn-dyn-transcript-flow
- **Severity**: important
- **Concern**: The finalization step always re-runs transcript capture when `RUN_ID` and `LARCH_CLAUDE_SOURCE_FILE` are set. On runs that already completed Step 7a, that can overwrite the staged transcript with a longer post-ship slice before teardown commits logs, changing corpus contents and heatmap inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-transcript-flow: Gate Step 18 `run-log capture-transcript` on absence of `.completed/step-7a-terminal` (or an equivalent Step 7a completion sentinel), and keep the unconditional path only for pre-7a bail/stall finalization.


