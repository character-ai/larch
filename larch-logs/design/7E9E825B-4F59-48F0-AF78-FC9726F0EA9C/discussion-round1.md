## Decision 1: All 3 OOS items still reproduce
- **Question**: Do OOS_1, OOS_2, and OOS_3 still reproduce against current code?
- **Resolution**: Yes. OOS_1 whole-tree fallback at `python/review_and_fix.py:929`/`:938`; OOS_2 non-lint drift re-scan at `:1148`; OOS_3 has no single-path / single-attempt `_verify_post_cleanup_state` regression (`:769`). None stale.
- **Source**: codebase

## Decision 2: OOS_3 handling — test-first
- **Question**: Test-first regression vs. proactively hardening the cleanup control flow?
- **Resolution**: Test-first. Add a partial / single-path verification regression for `_verify_post_cleanup_state`. Change `_verify_post_cleanup_state` or the cleanup control flow only if that test exposes a real bug. Reverses the prior run's decision #3 per recovered-panel pushback (7 of 8 reviewers).
- **Source**: user

## Decision 3: Fix breadth — broader hardening OK
- **Question**: Surgical 3-item fix vs. broader hardening of the stage/commit/rollback machinery?
- **Resolution**: Broader hardening of adjacent stage/commit/rollback code is allowed when it yields a cleaner result, provided every currently-passing `python/test_review_and_fix.py` behavior still holds and each code change ships fail-before / pass-after coverage.
- **Source**: user

## Decision 4: Hardening boundary — leave `_finalize_failed_cleanup` missing-snapshot restore as-is
- **Question**: Should the missing-snapshot whole-tree restore in `_finalize_failed_cleanup` change?
- **Resolution**: No. Leave the missing-snapshot whole-tree restore (`python/review_and_fix.py:835-841`) as-is. Restore-on-failure differs from stage-on-success; sweeping to restore a clean tree is acceptable there.
- **Source**: user (prior decision #4, retained)

## Decision 5: OOS_1 reference model
- **Question**: What is the safe pattern for the OOS_1 fix?
- **Resolution**: `_collect_self_review_stage_paths` (`python/review_and_fix.py:1023`) returns `[]` when the snapshot head is missing or empty; it has no whole-tree fallback. It is the reference model for the OOS_1 fix, not a fix target.
- **Source**: codebase

## Hard constraints
- Preserve normal snapshot-present stage / commit semantics on the happy path.
- Preserve the `STEP5_*` / `LOOP_STATUS` envelope and the lint-fix commit message grammar (`Address lint fixes after review round {round_num}: {reason}`).
- No launcher argv changes (see `.claude/rules/launcher-argv-test-coverage.md`).
- stdlib-only.
- Ship fail-before / pass-after regression coverage for every code change.
