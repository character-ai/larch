### OOS_1: [OUT_OF_SCOPE] architecture
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `python/larch/state/closeout.py:238-244` — `_pin_architectural_guidelines_note_best_effort` calls `pin_note_from_staged` only and does not use the `refresh_staged_assessment_for_current_head` retry in `ship_guidelines.py`. Out of scope because this diff does not touch closeout; the reported #5675 recurrence is on the ship pin path, which is fixed here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] risk-integration
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `python/larch/core/architectural_guidelines.py:503-510` — On drift recovery, assessment prose is carried forward without re-validation against a materially changed live diff. That is the explicit approved tradeoff in the plan (metadata-only refresh, no prompt-side reassessment). It is a product/design choice, not an implementation defect in this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] security
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `python/larch/core/architectural_guidelines.py:167-191` — `materialize_implementation_diff` still interpolates `base_remote`/`base_ref` into git argv without an allowlist regex (G-Sec-1 aspiration). Pre-existing; not introduced or amplified by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] risk-integration
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: `python/tests/implement/test_ship.py:4401-4417` — `test_pin_and_load_guidelines_note_returns_drop_notice_on_fingerprint_mismatch` still omits `repo_root`, but production always passes it (`ship.py:304-308`). A sidecar with a non-empty but corrupt `DIFF_FINGERPRINT` (e.g. `"mismatch"`) can now recover via refresh when `repo_root` is present, whereas the old code treated any live/stored fingerprint mismatch as unrecoverable. Why OOS: the plan explicitly keeps only empty `DIFF_FINGERPRINT` unrecoverable and leaves this test unchanged; this is an accepted tradeoff, not a plan gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] risk-integration
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `python/tests/core/test_architectural_guidelines.py:647-699` — There is no dedicated test that `refresh_staged_assessment_for_current_head` returns `False` when `DIFF_FINGERPRINT` is absent but `repo_root` is available. The plan documents that edge case but does not require a new test. Why OOS: pre-existing guard path, not newly introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] code-quality
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `python/tests/core/test_architectural_guidelines.py:563-629` — `test_refresh_staged_assessment_for_current_head_updates_staged_metadata` and `test_refresh_staged_assessment_for_current_head_recovers_when_diff_changes` now share nearly identical post-refresh assertions; only the pre-refresh fingerprint setup differs. Why OOS: redundant coverage is harmless and does not affect regression risk for the shipped fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

---

**Merge notes (not part of validator output):**

- **FINDING_5** merges input FINDING_5 and FINDING_12 (same corrupt-fingerprint validation gap; both `important`).
- **FINDING_7–9** map to input FINDING_9–11; IDs follow first-seen order after in-scope items.
- Input FINDING_7 (`c515fee0a` scope marker) and FINDING_8 (positive plan-match summary) are not actionable findings and are omitted.
- All five inventory slots appear in at least one `- **Reviewer(s)**:` line; `cursor-specialist-edge-cases` appears only in `[OUT_OF_SCOPE]` blocks.

