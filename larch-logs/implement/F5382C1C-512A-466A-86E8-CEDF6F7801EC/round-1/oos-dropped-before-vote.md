### OOS_1: [OUT_OF_SCOPE] Any-head fallback may surface stale assessment on rare pre-merge HEAD advance
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The new fallback at `final_report.py:234–237` renders a durable note whenever `not consumable` and `note_readable_any_head()`, without re-running `note_fingerprint_stale()`. That is correct after post-merge `git checkout main` (the intended fix), but on a rare pre-merge path where HEAD advanced without ship-loop invalidation, the final summary could show an assessment that no longer matches the implementation diff; the old code dropped and invalidated in that case. Deliberate Option B tradeoff; the reported bug does not require tightening this path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] `note_readable_any_head()` alias may drift from `durable_note_present()`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: At `architectural_guidelines.py:323–325`, `note_readable_any_head()` is currently a one-line alias for `durable_note_present()`. The separate name documents intent for final-report vs ship-loop semantics, but if the checks diverge later only one call site may get updated. No current behavioral bug; maintainability only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Pre-existing consumable-and-stale ordering skips step-8 invalidation
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Pre-existing ordering at `final_report.py:238–247`: when a note is consumable but fingerprint-stale, step 6 can render a persisted `DROPPED_NOTE_ARTIFACT` and step 8 never runs because `section` is already non-empty. This diff does not change that path; not introduced or amplified by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] `MERGE_RESULT` post-merge fallback lacks test coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: latent
- **Concern**: `_post_merge_context()` at `closeout.py:82–89` also keys off `MERGE_RESULT` in `finalize-state.sh` / `ship-pr-state.sh`, but closeout tests only cover the `post-merge-sentinel` path. If that fallback regresses, CI would still pass because current tests never hit it. Failure degrades to the existing pin attempt (fingerprint skip on `main`); not a coverage gap for the fix under review, but the `MERGE_RESULT` branch remains untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Add one test that omits the sentinel, seeds a post-merge MERGE_RESULT, and asserts _pin_architectural_guidelines_note_best_effort() still skips on mismatched HEAD.

### OOS_5: [OUT_OF_SCOPE] New closeout tests not pinned in shard map
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Six new tests in `python/shard-assignments.json` are not pinned in the shard map. Unassigned nodeids still run via round-robin in CI (`docs/linting.md`); shard hygiene only, not a functional regression for this change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

---

**Merge notes**

| Raw inputs | Merged into | Rationale |
|---|---|---|
| FINDING_2 + FINDING_5 | FINDING_3 | Same any-head / HEAD-mismatch risk; both OOS-only slots |
| FINDING_6 + FINDING_8 | FINDING_6 | Same `MERGE_RESULT` fallback test gap; both OOS-only slots |
| FINDING_9 vs FINDING_2/5 | Split (FINDING_2 vs FINDING_3) | Same code path, but sources distinguished in-scope (`codex-generalist`) from OOS (`cursor-*`) |
| FINDING_1 vs FINDING_4 | Separate | Same file region, different failure mode (drop-notice short-circuit vs pre-existing step ordering) |

**Slot inventory**: all five required slots appear in at least one `- **Reviewer(s)**:` line; `out-of-scope-only` slots appear only in `[OUT_OF_SCOPE]` blocks.

